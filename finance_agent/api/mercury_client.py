import os
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv
from decimal import Decimal
from pathlib import Path

# Load .env from the project root
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class MercuryClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("mercury_production_api_key")
        
        if not self.api_key:
            raise ValueError("Missing Mercury API Key. Please set 'mercury_production_api_key' in your .env file.")
        
        self.base_url = "https://api.mercury.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(method, url, headers=self.headers, timeout=15, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Mercury API Error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Fetches all accounts for the user."""
        data = self._request("GET", "accounts")
        return data.get("accounts", data.get("data", []))

    def get_categories(self) -> List[Dict[str, Any]]:
        """Fetches available categories."""
        data = self._request("GET", "categories")
        return data.get("categories", data.get("data", []))

    def get_transactions(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches transactions, optionally filtered by account_id."""
        endpoint = "transactions"
        params = {}
        if account_id:
            params['account_id'] = account_id
            
        data = self._request("GET", endpoint, params=params)
        return data.get("transactions", data.get("data", []))

    def update_transaction(self, account_id: str, transaction_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates a specific transaction."""
        endpoint = f"transaction/{transaction_id}"
        return self._request("PATCH", endpoint, json=update_data)
