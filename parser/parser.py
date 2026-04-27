# parser.py
import sys
from datetime import datetime, UTC

# ── FIX tag-35 lookup ───────────────────────────────────────────────────
MSG_TYPES = {
    "D": "NEW_ORDER",
    "8": "EXEC_REPORT",
    "F": "CANCEL",
    "G": "REPLACE",
    "9": "CANCEL_REJECT",
}


def decode(raw: str) -> dict:
    pairs = {}
    for field in raw.split("\x01"):
        if "=" in field:
            tag, _, val = field.partition("=")
            pairs[tag.strip()] = val.strip()
    return pairs


def format_msg(tags: dict) -> str:
    ts = datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]
    return (
        f"[{ts}] "
        f"seq={tags.get('34','?')} "
        f"type={MSG_TYPES.get(tags.get('35'), tags.get('35','?'))} "
        f"sym={tags.get('55','?')} "
        f"side={tags.get('54','?')} "
        f"qty={tags.get('38','?')} "
        f"px={tags.get('44','?')} "
        f"clordid={tags.get('11','?')}"
    )


def tags_to_order(tags: dict, raw: str) -> dict:
    """Convert decoded FIX tags into a dict suitable for insert_order()."""
    return {
        "cl_ord_id":      tags.get("11", ""),
        "symbol":         tags.get("55", ""),
        "side":           tags.get("54", ""),
        "msg_type":       MSG_TYPES.get(tags.get("35"), tags.get("35", "")),
        "order_qty":      tags.get("38"),
        "price":          tags.get("44"),
        "fill_price":     tags.get("31"),       # tag 31 = LastPx (fill price)
        "status":         tags.get("39"),        # tag 39 = OrdStatus
        "seq_num":        tags.get("34"),
        "sender_comp_id": tags.get("49"),
        "target_comp_id": tags.get("56"),
        "raw_fix":        raw,
    }


def main() -> None:
    # Lazy import so the parser can still run standalone for stdout-only use
    try:
        from database.connection import get_session
        from database.repository import insert_order, insert_anomaly, get_max_seq_num
        from analyzer import analyze_order, check_sequence_gap
        from notifier import send_slack_alert
        db_available = True
    except Exception:
        db_available = False
        print("[parser] WARNING: database unavailable, running in stdout-only mode", flush=True)

    # Cache to track the last sequence number per session within this batch
    session_cache = {}

    for line in sys.stdin:
        line = line.strip()
        if not line or "=" not in line:
            continue
        tags = decode(line)
        if not tags.get("35"):
            continue

        print(format_msg(tags), flush=True)

        if db_available:
            try:
                session = get_session()
                order_dict = tags_to_order(tags, line)
                
                sender = order_dict.get("sender_comp_id")
                target = order_dict.get("target_comp_id")
                s_key = (sender, target)

                # Initialize cache from DB if not already seen in this batch
                if s_key not in session_cache:
                    session_cache[s_key] = get_max_seq_num(session, sender, target)
                
                prev_max = session_cache[s_key]
                
                # Persist order
                inserted_order = insert_order(session, order_dict)
                
                # Flush so that raw SQL queries in analyzer (for duplicate ID checks) 
                # can see this record immediately.
                session.flush()

                # Run Anomaly Detection
                anomalies = analyze_order(session, inserted_order, tags)
                
                # Check specifically for sequence gap using our cached value
                gap = check_sequence_gap(session, inserted_order, prev_max)
                if gap:
                    anomalies.append(gap)
                
                # Update cache for the next message in this batch
                try:
                    session_cache[s_key] = int(order_dict.get("seq_num") or prev_max or 0)
                except (ValueError, TypeError):
                    pass

                # Persist and notify for all detected anomalies
                for anom in anomalies:
                    insert_anomaly(session, anom)
                    print(f"[parser] Alerting Slack: {anom['anomaly_type']} for order {inserted_order['id']}", flush=True)
                    send_slack_alert(anom, inserted_order)

                session.commit()
            except Exception as exc:
                session.rollback()
                print(f"[parser] DB error: {exc}", flush=True)
            finally:
                session.close()


if __name__ == "__main__":
    main()