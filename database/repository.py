"""
database.repository
~~~~~~~~~~~~~~~~~~~
All SQL read/write logic.  Nothing else belongs here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Order, Anomaly


# ── writes ──────────────────────────────────────────────────────────────

def insert_order(session: Session, order: dict) -> Order:
    """
    Persist a parsed FIX order dict and return the ORM object.

    Expected keys (all optional except raw_fix):
        cl_ord_id, symbol, side, msg_type, order_qty, price,
        fill_price, status, seq_num, sender_comp_id, target_comp_id, raw_fix
    """
    rec = Order(
        cl_ord_id=order.get("cl_ord_id", ""),
        symbol=order.get("symbol", ""),
        side=order.get("side", ""),
        msg_type=order.get("msg_type", ""),
        order_qty=order.get("order_qty"),
        price=order.get("price"),
        fill_price=order.get("fill_price"),
        status=order.get("status"),
        seq_num=order.get("seq_num"),
        sender_comp_id=order.get("sender_comp_id"),
        target_comp_id=order.get("target_comp_id"),
        raw_fix=order["raw_fix"],
    )
    session.add(rec)
    session.flush()           # assigns rec.id without committing
    return rec


def insert_anomaly(session: Session, anomaly: dict) -> Anomaly:
    """
    Persist an anomaly record.

    Required keys: order_id, anomaly_type, raw_fix
    Optional:      severity, description
    """
    rec = Anomaly(
        order_id=anomaly["order_id"],
        anomaly_type=anomaly["anomaly_type"],
        severity=anomaly.get("severity", "MEDIUM"),
        description=anomaly.get("description"),
        raw_fix=anomaly.get("raw_fix"),
    )
    session.add(rec)
    session.flush()
    return rec


# ── reads ───────────────────────────────────────────────────────────────

def get_orders_by_symbol(
    session: Session,
    symbol: str,
    *,
    limit: int = 100,
) -> Sequence[Order]:
    """Fetch orders for a given symbol, newest first (uses ix_orders_symbol_received)."""
    stmt = (
        select(Order)
        .where(Order.symbol == symbol)
        .order_by(Order.received_at.desc())
        .limit(limit)
    )
    return session.scalars(stmt).all()


def get_orders_by_cl_ord_id(session: Session, cl_ord_id: str) -> Sequence[Order]:
    """Fetch all order lifecycle events for a client order ID."""
    stmt = (
        select(Order)
        .where(Order.cl_ord_id == cl_ord_id)
        .order_by(Order.received_at)
    )
    return session.scalars(stmt).all()


def get_orders_in_range(
    session: Session,
    start: datetime,
    end: datetime,
    *,
    symbol: Optional[str] = None,
    limit: int = 500,
) -> Sequence[Order]:
    """Fetch orders within a time window, optionally filtered by symbol."""
    stmt = (
        select(Order)
        .where(Order.received_at.between(start, end))
    )
    if symbol:
        stmt = stmt.where(Order.symbol == symbol)
    stmt = stmt.order_by(Order.received_at.desc()).limit(limit)
    return session.scalars(stmt).all()


def get_anomalies_for_order(session: Session, order_id: int) -> Sequence[Anomaly]:
    """Get all anomalies associated with a specific order."""
    stmt = (
        select(Anomaly)
        .where(Anomaly.order_id == order_id)
        .order_by(Anomaly.detected_at)
    )
    return session.scalars(stmt).all()


def get_anomalies_by_type(
    session: Session,
    anomaly_type: str,
    *,
    limit: int = 100,
) -> Sequence[Anomaly]:
    """Fetch anomalies of a given type, newest first."""
    stmt = (
        select(Anomaly)
        .where(Anomaly.anomaly_type == anomaly_type)
        .order_by(Anomaly.detected_at.desc())
        .limit(limit)
    )
    return session.scalars(stmt).all()


def count_orders_by_symbol(session: Session, symbol: str) -> int:
    """Return the total count of orders for a symbol."""
    from sqlalchemy import func
    stmt = select(func.count()).select_from(Order).where(Order.symbol == symbol)
    return session.scalar(stmt) or 0
