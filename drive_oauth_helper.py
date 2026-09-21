#!/usr/bin/env python3
"""
Google Drive OAuth Helper for LDK Ops
Uses LDK International's dedicated GCP OAuth Client to authenticate Google Drive
for dailey@ldk-international.com without "app blocked" restrictions.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
import http.server
import socketserver
import threading
import argparse
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_FILES = {
    "business": SCRIPT_DIR / ".google_drive_token.json",
    "personal": SCRIPT_DIR / ".google_drive_token_personal.json",
}

def _load_env_secrets():
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_env_secrets()

# LDK International GCP Project OAuth Client
CLIENT_ID = os.environ.get("GOOGLE_DRIVE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_DRIVE_CLIENT_SECRET", "")

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.email"
]
REDIRECT_PORT = 8085
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"


def get_token_path(account: str = "business") -> Path:
    return TOKEN_FILES.get(account, TOKEN_FILES["business"])


def get_authorization_url(account: str = "business", login_hint: Optional[str] = None) -> str:
    """Generates the Google OAuth authorization URL for Google Drive."""
    if login_hint is None:
        login_hint = "dailey.kluck@gmail.com" if account == "personal" else "dailey@ldk-international.com"

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_URI}?{urllib.parse.urlencode(params)}"


def exchange_code(code_or_url: str, account: str = "business") -> bool:
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
            token_path = get_token_path(account)
            token_path.write_text(json.dumps(payload, indent=2))
            os.chmod(token_path, 0o600)
            print(f"\n✅ Google Drive credentials successfully saved to: {token_path.name}")
            
            # Verify drive access immediately
            verify_drive_access(token_data.get("access_token"))
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"\n❌ Failed to exchange code: {err_msg}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error exchanging code: {e}", file=sys.stderr)
        return False


def verify_drive_access(access_token: str):
    """Verifies access to Drive and prints current user info and top-level files."""
    try:
        req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req) as resp:
            uinfo = json.loads(resp.read().decode("utf-8"))
            print(f"👤 Authenticated as: {uinfo.get('email', 'Unknown')} ({uinfo.get('name', '')})")
    except Exception as e:
        print(f"ℹ️ User info check note: {e}")

    try:
        query = urllib.parse.quote("trashed = false and 'root' in parents")
        req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files?q={query}&pageSize=15&fields=files(id,name,mimeType)",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req) as resp:
            files_data = json.loads(resp.read().decode("utf-8"))
            items = files_data.get("files", [])
            print(f"\n📁 Root Drive Contents ({len(items)} items preview):")
            if not items:
                print("  (Root folder is empty)")
            for item in items:
                is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
                icon = "📁" if is_folder else "📄"
                print(f"  {icon} {item.get('name')} (ID: {item.get('id')})")
    except Exception as e:
        print(f"⚠️ Could not list Drive files: {e}")


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Local HTTP handler to capture authorization code from browser redirect."""
    captured_code = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            OAuthCallbackHandler.captured_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <html>
            <body style="font-family: -apple-system, sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: #0F9D58;">✅ Google Drive Authorization Successful!</h2>
                <p>Credentials received. You can now close this tab and return to Antigravity.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code parameter found in callback.")

    def log_message(self, format, *args):
        pass  # Suppress default server access logs


def run_local_listener(timeout=600):
    """Runs a temporary local web server to catch the OAuth redirect."""
    server = socketserver.TCPServer(("127.0.0.1", REDIRECT_PORT), OAuthCallbackHandler)
    server.timeout = 1.0
    elapsed = 0
    print(f"📡 Local listener active on {REDIRECT_URI}... Waiting for browser authorization.")
    while OAuthCallbackHandler.captured_code is None and elapsed < timeout:
        server.handle_request()
        elapsed += 1
    server.server_close()
    return OAuthCallbackHandler.captured_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LDK Ops Google Drive OAuth Helper")
    parser.add_argument("--account", choices=["business", "personal"], default="business", help="Target account (business: dailey@ldk-international.com, personal: dailey.kluck@gmail.com)")
    parser.add_argument("--code", help="Authorization code or redirected URL from browser")
    parser.add_argument("--no-listen", action="store_true", help="Do not run local server, only print link")
    args = parser.parse_args()

    if args.code:
        exchange_code(args.code, account=args.account)
    else:
        auth_url = get_authorization_url(account=args.account)
        expected_email = "dailey.kluck@gmail.com" if args.account == "personal" else "dailey@ldk-international.com"
        token_target = get_token_path(args.account)

        print(f"\n🔑 Google Drive Authorization Setup for LDK Ops ({args.account.capitalize()} Drive)")
        print("=" * 65)
        print(f"1. Open the following URL in your browser while logged into {expected_email}:")
        print(f"\n{auth_url}\n")
        print(f"2. Google will display the authorization screen.")
        print(f"3. When you approve, your browser will redirect to localhost:{REDIRECT_PORT} and save to {token_target.name}.")
        print(f"   (Or copy the redirected URL / code and run: python3 drive_oauth_helper.py --account {args.account} --code '<CODE>')\n")

        if not args.no_listen:
            code = run_local_listener(timeout=180)
            if code:
                exchange_code(code, account=args.account)
            else:
                print("⏱️ Listener timed out. You can re-run or pass --code directly.")
