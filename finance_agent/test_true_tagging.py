import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='/home/dailey/Development/ldk_ops/.env')
api_key = os.getenv("mercury_production_api_key") # Keep the secret-token: prefix
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
transaction_id = "a8c64a5e-757f-11f1-9acf-6b53d0ac80b0"

# The ID for 'Software & Subscriptions' which we found in the category list
target_category_id = "f3f3d654-7785-4332-883a-750d0baae56c"

print(f"Testing PATCH with categoryId: {target_category_id}")
url = f"https://api.mercury.com/api/v1/transaction/{transaction_id}"

# We'll try updating categoryId
r = requests.patch(url, headers=headers, json={"categoryId": target_category_id})
print(f"PATCH {r.status_code}: {r.text}")

# We'll also try updating the note at the same time to see if it accepts both
r = requests.patch(url, headers=headers, json={"note": "Testing category update", "categoryId": target_category_id})
print(f"PATCH (note + categoryId) {r.status_code}: {r.text}")
