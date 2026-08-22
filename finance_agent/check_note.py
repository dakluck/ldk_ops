import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dailey/Development/ldk_ops/.env')
api_key = os.getenv("mercury_production_api_key")
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
transaction_id = "a8c64a5e-757f-11f1-9acf-6b53d0ac80b0"

r = requests.get(f"https://api.mercury.com/api/v1/transaction/{transaction_id}", headers=headers)
print(f"Response: {r.json()}")
