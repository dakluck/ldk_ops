#!/usr/bin/env bash
set -e

SCRIPT_DIR="/home/dailey/Development/ldk_ops"
cd "$SCRIPT_DIR"

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/dailey/.local/bin:$PATH"
mkdir -p "$SCRIPT_DIR/logs"
LOG_FILE="$SCRIPT_DIR/logs/mbma_sync.log"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting MBMA School Calendar Daily Sync ===" | tee -a "$LOG_FILE"
/usr/bin/python3 "$SCRIPT_DIR/mbma_calendar_sync.py" --scan 2>&1 | tee -a "$LOG_FILE"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] MBMA School Calendar Daily Sync Completed ===" | tee -a "$LOG_FILE"
