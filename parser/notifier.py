"""
parser.notifier
~~~~~~~~~~~~~~~
Utility for sending alerts to external services (Slack).
"""

import os
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_alert(anomaly: dict, order: dict):
    """
    Sends a formatted alert to Slack for a detected anomaly.
    Converts UTC detection time to Central Time (CST/CDT).
    """
    if not SLACK_WEBHOOK_URL:
        print("[notifier] WARNING: SLACK_WEBHOOK_URL not set in environment.")
        return

    # Convert detected_at (UTC aware) to Central Time
    utc_dt = anomaly.get("detected_at")
    if isinstance(utc_dt, datetime):
        central_dt = utc_dt.astimezone(ZoneInfo("America/Chicago"))
        ts_str = central_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        ts_str = "N/A"
    
    # Use raw_fix from anomaly if available, otherwise from order
    raw_fix = anomaly.get("raw_fix") or order.get("raw_fix", "")
    # Truncate to 200 chars
    truncated_fix = (raw_fix[:200] + "..") if len(raw_fix) > 200 else raw_fix
    
    # Slack Payload
    payload = {
        "text": f"🚨 *FIX Anomaly Detected: {anomaly.get('anomaly_type')}*",
        "attachments": [
            {
                "color": "#FF0000" if anomaly.get("severity") == "CRITICAL" else "#FFA500",
                "fields": [
                    {"title": "Severity", "value": anomaly.get("severity", "MEDIUM"), "short": True},
                    {"title": "Symbol", "value": order.get("symbol", "N/A"), "short": True},
                    {"title": "MsgType", "value": order.get("msg_type", "N/A"), "short": True},
                    {"title": "Detected At", "value": ts_str, "short": True},
                    {"title": "Description", "value": anomaly.get("description", "No description"), "short": False},
                    {"title": "Raw FIX (Truncated)", "value": f"`{truncated_fix}`", "short": False}
                ],
                "footer": "FIX Analyzer Bot"
            }
        ]
    }
    
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        print(f"[notifier] Failed to send Slack alert: {e}")
