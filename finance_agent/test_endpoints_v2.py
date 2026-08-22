import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dailey/Development/ldk_ops/.env')
api_key = os.getenv("mercury_production_api_key").replace("secret-token:", "")
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
base_url = "https://api.mercury.com/api/v1"
account_id = "f4b609a0-f8b5-11f0-b80d-d7b976aafdf7"
transaction_id = "a8c64a5e-757f-11f1-9acf-6b53d0ac80b0"

endpoints = [
    f"accounts/{account_id}/transactions/{transaction_id}", # plural accounts
    f"account/{account_id}/transactions/{transaction_id}", # singular account
    f"transactions/{transaction_id}", # top level
]

for ep in endpoints:
    url = f"{base_url}/{ep}"
    print(f"Testing: {url}")
    r = requests.get(url, headers=headers)
    print(f"  GET {r.status_code}")
    r_patch = requests.patch(url, headers=headers, json={"note": "test"})
    print(f"  PATCH {r_patch.status_code}")
    print("-" * 20)
