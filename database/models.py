"""
database.models
~~~~~~~~~~~~~~~
SQLAlchemy ORM models for FIX order records and anomalies.
"""

from datetime import datetime, UTC

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared base for all models."""
    pass


class Order(Base):
    """A parsed FIX order or execution-report record."""

    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cl_ord_id = Column(String(64), nullable=False, comment="FIX tag 11")
    symbol = Column(String(32), nullable=False, comment="FIX tag 55")
    side = Column(String(4), nullable=False, comment="FIX tag 54 (1=Buy, 2=Sell)")
    msg_type = Column(String(16), nullable=False, comment="Human-readable msg type")
    order_qty = Column(DECIMAL(18, 6), nullable=True, comment="FIX tag 38")
    price = Column(DECIMAL(18, 6), nullable=True, comment="FIX tag 44")
    fill_price = Column(DECIMAL(18, 6), nullable=True, comment="Execution fill price")
    status = Column(String(32), nullable=True, comment="FIX tag 39 OrdStatus")
    seq_num = Column(Integer, nullable=True, comment="FIX tag 34")
    sender_comp_id = Column(String(64), nullable=True, comment="FIX tag 49")
    target_comp_id = Column(String(64), nullable=True, comment="FIX tag 56")
    raw_fix = Column(Text, nullable=False, comment="Original FIX message verbatim")
    received_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC),
        comment="Timestamp when record was persisted",
    )

    anomalies = relationship("Anomaly", back_populates="order", cascade="all, delete-orphan")

    # ---------- composite indexes for common queries ----------
    __table_args__ = (
        Index("ix_orders_symbol", "symbol"),
        Index("ix_orders_cl_ord_id", "cl_ord_id"),
        Index("ix_orders_msg_type", "msg_type"),
        Index("ix_orders_received_at", "received_at"),
        Index("ix_orders_symbol_received", "symbol", "received_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} sym={self.symbol} "
            f"type={self.msg_type} cl_ord_id={self.cl_ord_id}>"
        )


class Anomaly(Base):
    """An anomaly detected on a specific order."""

    __tablename__ = "anomalies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(
        BigInteger,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    anomaly_type = Column(String(64), nullable=False, comment="e.g. DUPLICATE, PRICE_SPIKE")
    severity = Column(String(16), nullable=True, default="MEDIUM")
    description = Column(Text, nullable=True)
    raw_fix = Column(Text, nullable=True, comment="Relevant FIX snippet")
    detected_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC),
    )

    order = relationship("Order", back_populates="anomalies")

    __table_args__ = (
        Index("ix_anomalies_order_id", "order_id"),
        Index("ix_anomalies_type", "anomaly_type"),
        Index("ix_anomalies_detected_at", "detected_at"),
    )

    def __repr__(self) -> str:
        return f"<Anomaly id={self.id} type={self.anomaly_type} order_id={self.order_id}>"
