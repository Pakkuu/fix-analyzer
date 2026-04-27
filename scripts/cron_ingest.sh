#!/bin/bash
# scripts/cron_ingest.sh
# Batch processes new log entries since the last run.

PROJECT_ROOT="/home/ubuntu/fix-analyzer"
LOG_FILE="$PROJECT_ROOT/logs/fix-session.log"
STATE_FILE="$PROJECT_ROOT/logs/ingest.state"
LOCK_FILE="/tmp/fix_analyzer_cron.lock"

# Use a lock file to prevent overlapping runs
exec 200>$LOCK_FILE
if ! flock -n 200; then
    echo "Another ingestion process is already running."
    exit 1
fi

# Ensure log exists
if [ ! -f "$LOG_FILE" ]; then
    exit 0
fi

# Move to project root so uv finds the correct environment
cd "$PROJECT_ROOT"

# Get previous offset
OFFSET=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
FILE_SIZE=$(stat -c%s "$LOG_FILE")

# Reset offset if file was truncated/rotated
if [ "$FILE_SIZE" -lt "$OFFSET" ]; then
    OFFSET=0
fi

# Calculate how many bytes to read
BYTES_TO_READ=$((FILE_SIZE - OFFSET))

if [ "$BYTES_TO_READ" -gt 0 ]; then
    # Use tail to read from the specific byte offset
    # tail -c +N starts at byte N (1-indexed)
    export PYTHONPATH="$PROJECT_ROOT"
    tail -c +$((OFFSET + 1)) "$LOG_FILE" | /home/ubuntu/.local/bin/uv run python3 "$PROJECT_ROOT/parser/parser.py"
    
    # Update state file
    echo "$FILE_SIZE" > "$STATE_FILE"
fi
