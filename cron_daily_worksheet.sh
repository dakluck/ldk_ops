#!/usr/bin/env bash
set -e

SCRIPT_DIR="/home/dailey/Development/ldk_ops"
cd "$SCRIPT_DIR"

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/dailey/.local/bin:$PATH"
export RMAPI_CONFIG="$SCRIPT_DIR/.rmapi"

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Starting Daily Worksheet Generation ==="
/usr/bin/python3 "$SCRIPT_DIR/daily_worksheet.py" --upload
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Daily Worksheet Delivered Successfully ==="
