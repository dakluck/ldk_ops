#!/usr/bin/env bash
set -e

SCRIPT_DIR="/home/dailey/Development/ldk_ops"
cd "$SCRIPT_DIR"

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/dailey/.local/bin:$PATH"
mkdir -p "$SCRIPT_DIR/logs"
LOG_FILE="$SCRIPT_DIR/logs/trash_schedule.log"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting Sunday Trash Schedule Sync ===" | tee -a "$LOG_FILE"
/usr/bin/python3 "$SCRIPT_DIR/trash_schedule.py" --send-invite 2>&1 | tee -a "$LOG_FILE" || true
/usr/bin/python3 "$SCRIPT_DIR/trash_schedule.py" --push-calendar 2>&1 | tee -a "$LOG_FILE" || true
/usr/bin/python3 "$SCRIPT_DIR/trash_schedule.py" --ics 2>&1 | tee -a "$LOG_FILE"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Trash Schedule Sync Completed ===" | tee -a "$LOG_FILE"
