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
        db_available = True
    except Exception:
        db_available = False
        print("[parser] WARNING: database unavailable, running in stdout-only mode", flush=True)

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
                
                # Check for sequence gap BEFORE inserting (to know previous state)
                prev_max = get_max_seq_num(
                    session, 
                    order_dict.get("sender_comp_id"), 
                    order_dict.get("target_comp_id")
                )
                
                # Persist order
                inserted_order = insert_order(session, order_dict)
                
                # Run Anomaly Detection
                anomalies = analyze_order(session, inserted_order, tags)
                
                # Check specifically for sequence gap
                gap = check_sequence_gap(session, inserted_order, prev_max)
                if gap:
                    anomalies.append(gap)
                
                # Persist all detected anomalies
                for anom in anomalies:
                    insert_anomaly(session, anom)

                session.commit()
            except Exception as exc:
                session.rollback()
                print(f"[parser] DB error: {exc}", flush=True)
            finally:
                session.close()


if __name__ == "__main__":
    main()