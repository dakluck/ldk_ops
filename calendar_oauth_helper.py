#!/usr/bin/env python3
"""
Google Calendar OAuth Helper for LDK Ops
Enables direct, authorized insertion of Family Calendar events (e.g. Trash & Recycling)
using Dailey's Google Account and saving credentials to .google_calendar_token.json.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_FILE = SCRIPT_DIR / ".google_calendar_token.json"

CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
)
CLIENT_SECRET = os.environ.get(
    "GOOGLE_CLIENT_SECRET",
    "d-FL95Q19q7MQmFpd7hHD0Ty"
)

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly"
]
REDIRECT_URI = "http://localhost:1"

def get_authorization_url():
    """Generates the Google OAuth authorization URL."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{AUTH_URI}?{urllib.parse.urlencode(params)}"

def exchange_code(code_or_url):
    """Exchanges an authorization code or redirect URL for refresh & access tokens."""
    code = code_or_url.strip()
    if "code=" in code:
        parsed = urllib.parse.urlparse(code)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [code])[0]

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URI,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
            payload = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": token_data.get("refresh_token"),
                "access_token": token_data.get("access_token"),
                "token_uri": TOKEN_URI,
                "scopes": SCOPES
            }
            TOKEN_FILE.write_text(json.dumps(payload, indent=2))
            print(f"✅ Google Calendar credentials successfully saved to: {TOKEN_FILE.name}")
            
            # Auto-detect Family calendar
            detect_family_calendar(token_data.get("access_token"))
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"❌ Failed to exchange code: {err_msg}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error exchanging code: {e}", file=sys.stderr)
        return False

def detect_family_calendar(access_token):
    """Lists user calendars and detects the Family Calendar."""
    req = urllib.request.Request(
        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            cal_data = json.loads(resp.read().decode("utf-8"))
            items = cal_data.get("items", [])
            print("\n📅 Found accessible Google Calendars:")
            family_found = False
            for item in items:
                summary = item.get("summary", "")
                cid = item.get("id", "")
                primary = item.get("primary", False)
                print(f"  • {summary} ({cid}) {'[Primary]' if primary else ''}")
                if "family" in summary.lower():
                    family_found = True
                    print(f"    🎯 Detected Family Calendar ID: {cid}")
            if not family_found:
                print("  ℹ️ No calendar explicitly titled 'Family' found. You can specify FAMILY_CALENDAR_ID in .env.")
    except Exception as e:
        print(f"⚠️ Could not list calendars: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LDK Ops Google Calendar OAuth Helper")
    parser.add_argument("--code", help="Authorization code or redirected URL from browser")
    args = parser.parse_args()

    if args.code:
        exchange_code(args.code)
    else:
        print("\n🔑 Google Calendar Authorization Setup for LDK Ops")
        print("1. Open the following URL in your browser to authorize access to your Google Calendar:")
        print(f"\n{get_authorization_url()}\n")
        print("2. After granting consent, copy the full URL from the browser address bar (it will start with http://localhost:1/?code=...)")
        print("3. Run this script again with the code/URL:")
        print("   python3 calendar_oauth_helper.py --code '<PASTED_URL_OR_CODE>'\n")
