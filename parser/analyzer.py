"""
parser.analyzer
~~~~~~~~~~~~~~~
Refined anomaly detection for specific FIX behaviors.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from database.repository import get_symbol_stats, check_cl_ord_id_exists

def analyze_order(session: Session, order: dict, raw_tags: dict) -> list[dict]:
    """
    Analyzes an order for:
    1. Fat Finger (Price/Qty deviation)
    2. Duplicate ClOrdID (Same session)
    3. Unknown OrigClOrdID (For Cancel/Replace)
    """
    anomalies = []
    
    # 1. Fat Finger Detection (New Orders only)
    if order.get("msg_type") == "NEW_ORDER":
        symbol = order.get("symbol")
        stats = get_symbol_stats(session, symbol)
        
        # Skip price check for Market Orders (OrdType=1)
        ord_type = raw_tags.get("40")
        if stats["avg_px"] is not None and ord_type != "1":
            try:
                curr_px = float(order.get("price") or 0)
                # Flag if price deviates > 50% from recent average
                if abs(curr_px - stats["avg_px"]) / stats["avg_px"] > 0.5:
                    anomalies.append({
                        "order_id": order["id"],
                        "anomaly_type": "FAT_FINGER",
                        "severity": "HIGH",
                        "description": f"Price {curr_px} deviates significantly from avg {stats['avg_px']:.2f}",
                        "raw_fix": order.get("raw_fix")
                    })
            except (ValueError, TypeError):
                pass
        
        if stats["avg_qty"] is not None:
            try:
                curr_qty = float(order.get("order_qty") or 0)
                # Flag if quantity is 10x larger than average
                if curr_qty > stats["avg_qty"] * 10:
                    anomalies.append({
                        "order_id": order["id"],
                        "anomaly_type": "FAT_FINGER",
                        "severity": "HIGH",
                        "description": f"Quantity {curr_qty} is 10x larger than avg {stats['avg_qty']:.2f}",
                        "raw_fix": order.get("raw_fix")
                    })
            except (ValueError, TypeError):
                pass

    # 2. Duplicate ClOrdID (Same Session)
    if order.get("msg_type") == "NEW_ORDER":
        cl_ord_id = order.get("cl_ord_id")
        sender = order.get("sender_comp_id")
        
        if cl_ord_id and sender:
            # Check if another record exists with this ClOrdID and Sender
            sql = text("SELECT COUNT(*) FROM orders WHERE cl_ord_id = :cid AND sender_comp_id = :sender")
            count = session.execute(sql, {"cid": cl_ord_id, "sender": sender}).scalar()
            if count > 1:
                anomalies.append({
                    "order_id": order["id"],
                    "anomaly_type": "DUPLICATE_CLORDID",
                    "severity": "CRITICAL",
                    "description": f"Duplicate ClOrdID {cl_ord_id} in session {sender}",
                    "raw_fix": order.get("raw_fix")
                })

    # 3. Unknown OrigClOrdID (Cancel/Replace)
    if order.get("msg_type") in ["CANCEL", "REPLACE"]:
        # Tag 41 is OrigClOrdID
        orig_id = raw_tags.get("41")
        if orig_id:
            if not check_cl_ord_id_exists(session, orig_id):
                anomalies.append({
                    "order_id": order["id"],
                    "anomaly_type": "UNKNOWN_ORIG_CLORDID",
                    "severity": "MEDIUM",
                    "description": f"Referred OrigClOrdID {orig_id} not found in database",
                    "raw_fix": order.get("raw_fix")
                })

    return anomalies

def check_sequence_gap(session: Session, order: dict, prev_max_seq: int) -> dict | None:
    """Detects missing or out-of-order MsgSeqNum (Tag 34)."""
    curr_seq = order.get("seq_num")
    if curr_seq is None or prev_max_seq is None:
        return None
        
    try:
        if int(curr_seq) != int(prev_max_seq) + 1:
            return {
                "order_id": order["id"],
                "anomaly_type": "SEQUENCE_GAP",
                "severity": "LOW",
                "description": f"Sequence gap: expected {int(prev_max_seq) + 1}, got {curr_seq}",
                "raw_fix": order.get("raw_fix")
            }
    except (ValueError, TypeError):
        pass
    return None
