# parser.py
import sys
import time
from pathlib import Path
from datetime import datetime, UTC

LOG_FILE = Path(__file__).parent.parent / "logs" / "fix-session.log"

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


def tail(path: Path, from_start: bool = False):
    with open(path, "r") as f:
        if not from_start:
            f.seek(0, 2)  # jump to end for live-tail mode
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line.strip()


def main() -> None:
    from_start = "--all" in sys.argv
    print(f"Parser running... (log: {LOG_FILE})")
    for line in tail(LOG_FILE, from_start=from_start):
        if not line or "=" not in line:
            continue
        tags = decode(line)
        if not tags.get("35"):
            continue
        print(format_msg(tags))


if __name__ == "__main__":
    main()