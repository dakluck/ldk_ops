import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / '.env')
api_key = os.getenv("mercury_production_api_key")
if api_key.startswith("secret-token:"):
    api_key = api_key.replace("secret-token:", "", 1)

headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
url = "https://api.mercury.com/api/v1/account/f4b609a0-f8b5-11f0-b80d-d7b976aafdf7/transactions/a8c64a5e-757f-11f1-9acf-6b53d0ac80b0"

r = requests.get(url, headers=headers)
print(f"GET status: {r.status_code}")
print(f"GET response: {r.text}")

r_patch = requests.patch(url, headers=headers, json={"note": "test"})
print(f"PATCH status: {r_patch.status_code}")
print(f"PATCH response: {r_patch.text}")
