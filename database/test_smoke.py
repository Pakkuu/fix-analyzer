#!/usr/bin/env python3
"""Quick smoke test: insert sample FIX orders, query them back (Raw SQL version)."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.parser import decode, tags_to_order
from database.connection import get_session
from database.repository import (
    insert_order, insert_anomaly,
    get_orders_by_symbol, get_orders_by_cl_ord_id,
    get_anomalies_for_order, count_orders_by_symbol,
)

SAMPLE_MESSAGES = [
    "8=FIX.4.2\x0135=D\x0149=SENDER\x0156=TARGET\x0134=2\x0111=ORD002\x0155=AAPL\x0154=1\x0138=100\x0144=150.25\x0140=2\x01",
    "8=FIX.4.2\x0135=8\x0149=TARGET\x0156=SENDER\x0134=3\x0111=ORD002\x0155=AAPL\x0154=1\x0138=100\x0144=150.25\x0131=150.20\x0139=2\x01",
    "8=FIX.4.2\x0135=D\x0149=SENDER\x0156=TARGET\x0134=4\x0111=ORD003\x0155=MSFT\x0154=2\x0138=200\x0144=420.00\x0140=2\x01",
    "8=FIX.4.2\x0135=F\x0149=SENDER\x0156=TARGET\x0134=5\x0111=ORD003\x0155=MSFT\x0154=2\x0138=200\x0144=420.00\x01",
]


def main():
    session = get_session()
    try:
        # ── Insert orders ───────────────────────────────────────────
        print("═══ Inserting sample FIX orders ═══")
        inserted = []
        for raw in SAMPLE_MESSAGES:
            tags = decode(raw)
            order_dict = tags_to_order(tags, raw)
            rec = insert_order(session, order_dict)
            inserted.append(rec)
            print(f"  ✓ id={rec['id']}  sym={rec['symbol']:<6} type={rec['msg_type']:<14} "
                  f"cl_ord_id={rec['cl_ord_id']}  px={rec['price']}  fill={rec['fill_price']}")
        session.commit()

        # ── Insert an anomaly ───────────────────────────────────────
        print("\n═══ Inserting sample anomaly ═══")
        anom = insert_anomaly(session, {
            "order_id": inserted[0]["id"],
            "anomaly_type": "PRICE_SPIKE",
            "severity": "HIGH",
            "description": "Price moved >5% in 1 second",
            "raw_fix": SAMPLE_MESSAGES[0],
        })
        session.commit()
        print(f"  ✓ anomaly id={anom['id']}  type={anom['anomaly_type']}  "
              f"severity={anom['severity']}  order_id={anom['order_id']}")

        # ── Queries ─────────────────────────────────────────────────
        print("\n═══ Query: AAPL orders ═══")
        for o in get_orders_by_symbol(session, "AAPL"):
            print(f"  id={o['id']}  cl_ord_id={o['cl_ord_id']}  type={o['msg_type']}  "
                  f"px={o['price']}  fill={o['fill_price']}")

        print("\n═══ Query: ORD002 lifecycle ═══")
        for o in get_orders_by_cl_ord_id(session, "ORD002"):
            print(f"  id={o['id']}  type={o['msg_type']}  status={o['status']}")

        print(f"\n═══ Count: {count_orders_by_symbol(session, 'AAPL')} AAPL orders total ═══")
        print(f"═══ Count: {count_orders_by_symbol(session, 'MSFT')} MSFT orders total ═══")

        print("\n═══ Query: anomalies for order {0} ═══".format(inserted[0]['id']))
        for a in get_anomalies_for_order(session, inserted[0]['id']):
            print(f"  id={a['id']}  type={a['anomaly_type']}  severity={a['severity']}")

        print("\n✅ All tests passed!")

    except Exception as exc:
        session.rollback()
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
