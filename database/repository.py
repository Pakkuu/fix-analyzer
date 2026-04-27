"""
database.repository
~~~~~~~~~~~~~~~~~~~
All SQL read/write logic using raw SQL (no ORM).
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional, Sequence, Any

from sqlalchemy import text
from sqlalchemy.orm import Session


# ── writes ──────────────────────────────────────────────────────────────

def insert_order(session: Session, order: dict) -> dict:
    """
    Persist a parsed FIX order record using raw SQL.
    Returns a dict with the inserted record data (including 'id').
    """
    sql = text("""
        INSERT INTO orders (
            cl_ord_id, symbol, side, msg_type, order_qty, price,
            fill_price, status, seq_num, sender_comp_id, target_comp_id,
            raw_fix, received_at
        ) VALUES (
            :cl_ord_id, :symbol, :side, :msg_type, :order_qty, :price,
            :fill_price, :status, :seq_num, :sender_comp_id, :target_comp_id,
            :raw_fix, :received_at
        )
    """)
    
    # Ensure received_at is set if not provided
    received_at = order.get("received_at") or datetime.now(UTC)
    
    params = {
        "cl_ord_id":      order.get("cl_ord_id", ""),
        "symbol":         order.get("symbol", ""),
        "side":           order.get("side", ""),
        "msg_type":       order.get("msg_type", ""),
        "order_qty":      order.get("order_qty"),
        "price":          order.get("price"),
        "fill_price":     order.get("fill_price"),
        "status":         order.get("status"),
        "seq_num":        order.get("seq_num"),
        "sender_comp_id": order.get("sender_comp_id"),
        "target_comp_id": order.get("target_comp_id"),
        "raw_fix":        order["raw_fix"],
        "received_at":    received_at,
    }
    
    result = session.execute(sql, params)
    inserted_id = result.lastrowid
    
    # Return a dict version of the record
    return {**params, "id": inserted_id}


def insert_anomaly(session: Session, anomaly: dict) -> dict:
    """
    Persist an anomaly record using raw SQL.
    """
    sql = text("""
        INSERT INTO anomalies (
            order_id, anomaly_type, severity, description, raw_fix, detected_at
        ) VALUES (
            :order_id, :anomaly_type, :severity, :description, :raw_fix, :detected_at
        )
    """)
    
    detected_at = anomaly.get("detected_at") or datetime.now(UTC)
    
    params = {
        "order_id":     anomaly["order_id"],
        "anomaly_type": anomaly["anomaly_type"],
        "severity":     anomaly.get("severity", "MEDIUM"),
        "description":  anomaly.get("description"),
        "raw_fix":      anomaly.get("raw_fix"),
        "detected_at":  detected_at,
    }
    
    result = session.execute(sql, params)
    inserted_id = result.lastrowid
    
    return {**params, "id": inserted_id}


# ── reads ───────────────────────────────────────────────────────────────

def _to_dicts(rows) -> list[dict]:
    """Helper to convert SQLAlchemy Row objects to dicts."""
    return [dict(row._mapping) for row in rows]


def get_orders_by_symbol(
    session: Session,
    symbol: str,
    *,
    limit: int = 100,
) -> list[dict]:
    """Fetch orders for a given symbol, newest first."""
    sql = text("""
        SELECT * FROM orders 
        WHERE symbol = :symbol 
        ORDER BY received_at DESC 
        LIMIT :limit
    """)
    result = session.execute(sql, {"symbol": symbol, "limit": limit})
    return _to_dicts(result.all())


def get_orders_by_cl_ord_id(session: Session, cl_ord_id: str) -> list[dict]:
    """Fetch all order lifecycle events for a client order ID."""
    sql = text("""
        SELECT * FROM orders 
        WHERE cl_ord_id = :cl_ord_id 
        ORDER BY received_at ASC
    """)
    result = session.execute(sql, {"cl_ord_id": cl_ord_id})
    return _to_dicts(result.all())


def get_orders_in_range(
    session: Session,
    start: datetime,
    end: datetime,
    *,
    symbol: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Fetch orders within a time window, optionally filtered by symbol."""
    if symbol:
        sql = text("""
            SELECT * FROM orders 
            WHERE received_at BETWEEN :start AND :end 
              AND symbol = :symbol
            ORDER BY received_at DESC 
            LIMIT :limit
        """)
        params = {"start": start, "end": end, "symbol": symbol, "limit": limit}
    else:
        sql = text("""
            SELECT * FROM orders 
            WHERE received_at BETWEEN :start AND :end
            ORDER BY received_at DESC 
            LIMIT :limit
        """)
        params = {"start": start, "end": end, "limit": limit}
        
    result = session.execute(sql, params)
    return _to_dicts(result.all())


def get_anomalies_for_order(session: Session, order_id: int) -> list[dict]:
    """Get all anomalies associated with a specific order."""
    sql = text("""
        SELECT * FROM anomalies 
        WHERE order_id = :order_id 
        ORDER BY detected_at ASC
    """)
    result = session.execute(sql, {"order_id": order_id})
    return _to_dicts(result.all())


def get_anomalies_by_type(
    session: Session,
    anomaly_type: str,
    *,
    limit: int = 100,
) -> list[dict]:
    """Fetch anomalies of a given type, newest first."""
    sql = text("""
        SELECT * FROM anomalies 
        WHERE anomaly_type = :anomaly_type 
        ORDER BY detected_at DESC 
        LIMIT :limit
    """)
    result = session.execute(sql, {"anomaly_type": anomaly_type, "limit": limit})
    return _to_dicts(result.all())


def count_orders_by_symbol(session: Session, symbol: str) -> int:
    """Return the total count of orders for a symbol."""
    sql = text("SELECT COUNT(*) FROM orders WHERE symbol = :symbol")
    result = session.execute(sql, {"symbol": symbol})
    return result.scalar() or 0


def get_max_seq_num(session: Session, sender_comp_id: str, target_comp_id: str) -> Optional[int]:
    """Get the highest sequence number seen for a specific session."""
    sql = text("""
        SELECT MAX(seq_num) FROM orders 
        WHERE sender_comp_id = :sender AND target_comp_id = :target
    """)
    result = session.execute(sql, {"sender": sender_comp_id, "target": target_comp_id}).scalar()
    return int(result) if result is not None else None


def check_cl_ord_id_exists(session: Session, cl_ord_id: str, sender_comp_id: str = None) -> bool:
    """Check if a ClOrdID has been used before, optionally filtered by session/sender."""
    if sender_comp_id:
        sql = text("SELECT 1 FROM orders WHERE cl_ord_id = :cl_ord_id AND sender_comp_id = :sender LIMIT 1")
        params = {"cl_ord_id": cl_ord_id, "sender": sender_comp_id}
    else:
        sql = text("SELECT 1 FROM orders WHERE cl_ord_id = :cl_ord_id LIMIT 1")
        params = {"cl_ord_id": cl_ord_id}
        
    result = session.execute(sql, params).fetchone()
    return result is not None


def get_symbol_stats(session: Session, symbol: str) -> dict:
    """Get average price and quantity for the last 20 orders of a symbol."""
    sql = text("""
        SELECT AVG(price) as avg_px, AVG(order_qty) as avg_qty 
        FROM (
            SELECT price, order_qty FROM orders 
            WHERE symbol = :symbol AND msg_type = 'NEW_ORDER'
              AND price IS NOT NULL AND order_qty IS NOT NULL
            ORDER BY received_at DESC LIMIT 20
        ) as recent
    """)
    row = session.execute(sql, {"symbol": symbol}).fetchone()
    if not row or row[0] is None:
        return {"avg_px": None, "avg_qty": None}
    return {"avg_px": float(row[0]), "avg_qty": float(row[1])}
