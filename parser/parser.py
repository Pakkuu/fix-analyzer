# parser.py
import sys
import time
from datetime import datetime, UTC

LOG_FILE = "../logs/fix-session.log"

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
        f"type={tags.get('35','?')} "
        f"sym={tags.get('55','?')} "
        f"side={tags.get('54','?')} "
        f"qty={tags.get('38','?')} "
        f"px={tags.get('44','?')} "
        f"clordid={tags.get('11','?')}"
    )

def tail(path: str):
    with open(path, "r") as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line.strip()

def main() -> None:
    print("Parser running...")
    for line in tail(LOG_FILE):
        if not line or "=" not in line:
            continue
        tags = decode(line)
        if not tags.get("35"):
            continue
        print(format_msg(tags))

if __name__ == "__main__":
    main()