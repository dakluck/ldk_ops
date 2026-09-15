#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RMAPI_BIN="$SCRIPT_DIR/bin/rmapi"
CONFIG_FILE="$SCRIPT_DIR/.rmapi"

echo "========================================================"
echo "  reMarkable 2 Cloud Sync Setup (rmapi v0.0.35)"
echo "========================================================"
echo ""

if [ ! -f "$RMAPI_BIN" ]; then
    echo "⬇️ Downloading ddvk/rmapi v0.0.35..."
    mkdir -p "$SCRIPT_DIR/bin"
    curl -L -s https://github.com/ddvk/rmapi/releases/download/v0.0.35/rmapi-linux-amd64.tar.gz | tar -xz -C "$SCRIPT_DIR/bin/"
    chmod +x "$RMAPI_BIN"
fi

export RMAPI_CONFIG="$CONFIG_FILE"

if [ -n "$1" ]; then
    PAIRING_CODE="$1"
else
    echo "1. Open this URL in your browser:"
    echo "   👉 https://my.remarkable.com/device/browser/connect"
    echo "      (or https://my.remarkable.com/device/desktop/connect)"
    echo ""
    echo "2. Copy the 8-character one-time code."
    echo ""
    read -p "Enter one-time code: " PAIRING_CODE
fi

if [ -z "$PAIRING_CODE" ]; then
    echo "❌ No code entered. Aborting."
    exit 1
fi

echo "Authenticating with code: $PAIRING_CODE ..."
echo "$PAIRING_CODE" | "$RMAPI_BIN" -ni=false version > /dev/null 2>&1 || true

# Test listing
echo "Testing reMarkable Cloud connection..."
if "$RMAPI_BIN" -ni ls > /dev/null 2>&1; then
    echo "🎉 Success! Your reMarkable 2 is now paired with LDK Ops."
    echo ""
    echo "Uploading today's worksheet to /Daily/ ..."
    python3 "$SCRIPT_DIR/daily_worksheet.py" --upload
else
    echo "⚠️ Pairing failed or code expired. Please generate a fresh code and retry:"
    echo "  ./setup_rmapi.sh <8-char-code>"
fi
