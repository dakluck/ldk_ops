"""
Apple Search Ads (ASA) Campaign Management API Client (v4/v5)
Handles JWT generation, OAuth2 bearer token exchange, and campaign operations.
"""
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

class AppleSearchAdsClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        team_id: Optional[str] = None,
        key_id: Optional[str] = None,
        private_key_path: Optional[str] = None,
        org_id: Optional[str] = None
    ):
        self.client_id = client_id or os.getenv("ASA_CLIENT_ID")
        self.team_id = team_id or os.getenv("ASA_TEAM_ID")
        self.key_id = key_id or os.getenv("ASA_KEY_ID")
        self.private_key_path = private_key_path or os.getenv("ASA_PRIVATE_KEY_PATH")
        self.org_id = org_id or os.getenv("ASA_ORG_ID")

        self.base_url = "https://api.searchads.apple.com/api/v4"
        self.auth_url = "https://appleid.apple.com/auth/oauth2/token"
        self._access_token = None
        self._token_expiry = 0

    @property
    def is_configured(self) -> bool:
        return bool(
            self.client_id
            and self.team_id
            and self.key_id
            and self.private_key_path
            and os.path.exists(os.path.expanduser(self.private_key_path))
        )

    def _generate_client_assertion(self) -> str:
        """Generates an ES256 signed JWT assertion for Apple OAuth2."""
        try:
            import jwt
        except ImportError:
            raise ImportError("PyJWT with cryptography required: pip install 'pyjwt[crypto]'")

        key_path = Path(os.path.expanduser(self.private_key_path))
        private_key = key_path.read_text()

        now = int(time.time())
        payload = {
            "sub": self.client_id,
            "aud": "https://appleid.apple.com",
            "iat": now,
            "exp": now + 86400,  # 24 hours max
            "iss": self.team_id,
        }
        headers = {
            "kid": self.key_id,
            "alg": "ES256"
        }
        return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)

    def get_access_token(self) -> str:
        """Fetches or returns an existing valid Bearer access token."""
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        if not self.is_configured:
            raise RuntimeError("Apple Search Ads credentials not configured in .env.")

        client_assertion = self._generate_client_assertion()
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_assertion,
            "scope": "searchadsorg"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(self.auth_url, data=data, headers=headers, timeout=15)
        response.raise_for_status()
        token_data = response.json()

        self._access_token = token_data["access_token"]
        self._token_expiry = time.time() + token_data.get("expires_in", 3600)
        return self._access_token

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Makes an authenticated request to the ASA REST API."""
        if not self.is_configured:
            return {"simulated": True, "data": []}

        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-AP-Context": f"orgId={self.org_id}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        res = requests.request(method, url, headers=headers, timeout=20, **kwargs)
        res.raise_for_status()
        return res.json()

    def get_campaigns(self) -> List[Dict[str, Any]]:
        """Retrieves list of active campaigns."""
        if not self.is_configured:
            # Return blueprint configuration if not live
            return [
                {
                    "id": "mock_camp_01",
                    "name": "Reference iOS - Exact Category Discovery",
                    "status": "CONFIGURED_BLUEPRINT",
                    "dailyBudgetAmount": {"amount": "5.00", "currency": "USD"},
                    "targetCPI": 1.82,
                    "adamId": "6739818812"
                }
            ]
        data = self._request("GET", "campaigns")
        return data.get("data", [])

    def get_campaign_reports(self, campaign_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetches daily aggregate performance report (impressions, taps, installs, spend)."""
        if not self.is_configured:
            return {
                "impressions": 0,
                "taps": 0,
                "installs": 0,
                "avgCPT": 0.0,
                "avgCPI": 0.0,
                "totalSpend": 0.0,
                "status": "Awaiting Live ASA Credentials"
            }
        body = {
            "startTime": f"{start_date}T00:00:00.000",
            "endTime": f"{end_date}T23:59:59.000",
            "timeZone": "UTC",
            "granularity": "DAILY",
            "selector": {
                "orderBy": [{"field": "spend", "sortOrder": "DESCENDING"}],
                "pagination": {"offset": 0, "limit": 100}
            }
        }
        return self._request("POST", f"reports/campaigns/{campaign_id}", json=body)

if __name__ == "__main__":
    client = AppleSearchAdsClient()
    print("ASA Client Configured:", client.is_configured)
    print("Campaigns:", client.get_campaigns())
