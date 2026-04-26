# parser.py
import sys
from datetime import datetime, UTC

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


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line or "=" not in line:
            continue
        tags = decode(line)
        if tags.get("35"):
            print(format_msg(tags), flush=True)


if __name__ == "__main__":
    main()