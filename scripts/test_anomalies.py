#!/usr/bin/env python3
import sys
import os
import subprocess
import time

# Add root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_session
from database.repository import get_anomalies_for_order

# 1. Populate baseline for Fat Finger (10 orders at px=100)
BASELINE = [
    f"8=FIX.4.2\x0135=D\x0149=SENDER\x0156=TARGET\x0134={i}\x0111=B_{i}\x0155=AAPL\x0154=1\x0138=10\x0144=100.00\x01"
    for i in range(1, 11)
]

# 2. Anomalous messages
ANOMALIES = [
    # Sequence Gap: Jump from 10 to 12
    "8=FIX.4.2\x0135=D\x0149=SENDER\x0156=TARGET\x0134=12\x0111=GAP_01\x0155=AAPL\x0154=1\x0138=10\x0144=100.00\x01",
    # Fat Finger: Price 200 (100% dev from 100)
    "8=FIX.4.2\x0135=D\x0149=SENDER\x0156=TARGET\x0134=13\x0111=FAT_01\x0155=AAPL\x0154=1\x0138=10\x0144=200.00\x01",
    # Duplicate ClOrdID: Reuse B_1
    "8=FIX.4.2\x0135=D\x0149=SENDER\x0156=TARGET\x0134=14\x0111=B_1\x0155=AAPL\x0154=1\x0138=10\x0144=100.00\x01",
    # Unknown OrigClOrdID: Cancel for non-existent ID
    "8=FIX.4.2\x0135=F\x0149=SENDER\x0156=TARGET\x0134=15\x0111=CAN_01\x0141=NONEXISTENT\x0155=AAPL\x0154=1\x01",
]

def run_test():
    print("═══ Running Refined Anomaly Detection Test ═══")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    all_msgs = BASELINE + ANOMALIES
    input_str = "\n".join(all_msgs) + "\n"
    
    process = subprocess.Popen(
        ["uv", "run", "python3", "parser/parser.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    stdout, stderr = process.communicate(input=input_str)
    
    # Check database for anomalies
    session = get_session()
    try:
        from sqlalchemy import text
        # Get orders created in this test run (roughly)
        sql = text("SELECT id, cl_ord_id, seq_num, msg_type FROM orders ORDER BY id DESC LIMIT 14")
        orders = session.execute(sql).fetchall()
        
        print("\nChecking Anomalies in DB:")
        # Reverse to show in chronological order
        for order in reversed(orders):
            oid, cid, seq, mtype = order
            anoms = get_anomalies_for_order(session, oid)
            if not anoms and seq <= 10: continue # Skip baseline
            
            print(f"Order {oid} ({mtype}) Seq={seq} ClOrdID={cid}: {len(anoms)} anomalies")
            for a in anoms:
                print(f"  - [{a['severity']}] {a['anomaly_type']}: {a['description']}")
    finally:
        session.close()

if __name__ == "__main__":
    run_test()
