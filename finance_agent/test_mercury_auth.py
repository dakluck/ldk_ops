import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dailey/Development/ldk_ops/.env')
full_token = os.getenv("mercury_production_api_key")
clean_token = full_token.replace("secret-token:", "")

transaction_id = "a8c64a5e-757f-11f1-9acf-6b53d0ac80b0"

print(f"Full Token: {full_token[:20]}...")
print(f"Clean Token: {clean_token[:20]}...")

# 1. Test with Bearer + secret-token: (which is what the API might expect)
headers_full = {"Authorization": f"Bearer {full_token}", "Content-Type": "application/json"}
r = requests.get(f"https://api.mercury.com/api/v1/transaction/{transaction_id}", headers=headers_full)
print(f"GET with full token: {r.status_code} - {r.text[:100]}")

# 2. Test with Bearer + clean token
headers_clean = {"Authorization": f"Bearer {clean_token}", "Content-Type": "application/json"}
r = requests.get(f"https://api.mercury.com/api/v1/transaction/{transaction_id}", headers=headers_clean)
print(f"GET with clean token: {r.status_code} - {r.text[:100]}")
