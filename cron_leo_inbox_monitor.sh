#!/usr/bin/env bash
set -e

SCRIPT_DIR="/home/dailey/Development/ldk_ops"
cd "$SCRIPT_DIR"

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/dailey/.local/bin:$PATH"
mkdir -p "$SCRIPT_DIR/logs"
LOG_FILE="$SCRIPT_DIR/logs/leo_inbox_monitor.log"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting Leo Inbox Monitor Run ===" >> "$LOG_FILE"
/usr/bin/python3 "$SCRIPT_DIR/leo_inbox_monitor.py" --check-once 2>&1 >> "$LOG_FILE"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Leo Inbox Monitor Run Completed ===" >> "$LOG_FILE"
