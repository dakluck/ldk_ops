import json
import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

CLIENT_CONFIG = {
    "installed": {
        "client_id": "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com",
        "client_secret": "d-FL95Q19q7MQmFpd7hHD0Ty",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/datastore",
    "https://www.googleapis.com/auth/userinfo.email"
]

REDIRECT_URI = "http://localhost:1"
STATE_FILE = Path(__file__).resolve().parent / ".gcloud_pending_auth.json"
ADC_FILE = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"

def get_auth_url():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    STATE_FILE.write_text(json.dumps({
        "state": state,
        "code_verifier": flow.code_verifier,
        "redirect_uri": REDIRECT_URI
    }))
    return auth_url

def exchange_code(code_or_url):
    if not STATE_FILE.exists():
        raise RuntimeError("No pending auth session found.")
    
    state_data = json.loads(STATE_FILE.read_text())
    
    # Extract code if full URL was pasted
    code = code_or_url
    if "code=" in code_or_url:
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(code_or_url)
        params = parse_qs(parsed.query)
        code = params.get("code", [code_or_url])[0]

    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=state_data["redirect_uri"],
        state=state_data["state"],
        code_verifier=state_data["code_verifier"]
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    adc_payload = {
        "account": "",
        "client_id": CLIENT_CONFIG["installed"]["client_id"],
        "client_secret": CLIENT_CONFIG["installed"]["client_secret"],
        "quota_project_id": "reference-482005",
        "refresh_token": creds.refresh_token,
        "type": "authorized_user",
        "universe_domain": "googleapis.com"
    }
    ADC_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADC_FILE.write_text(json.dumps(adc_payload, indent=2))
    STATE_FILE.unlink(missing_ok=True)
    print("✅ Application Default Credentials successfully refreshed!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        exchange_code(sys.argv[1])
    else:
        print(get_auth_url())
