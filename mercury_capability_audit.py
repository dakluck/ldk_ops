import os
import requests
from dotenv import load_dotenv

def audit_mercury_capabilities():
    """
    Audits the Mercury API to determine if it supports updating/patching transactions.
    """
    # 1. Load environment variables
    load_dotenv()
    api_key = os.getenv("mercury_production_api_key")

    if not api_key:
        print("Error: 'mercury_production_api_key' not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # 2. Get first account
        accounts_url = "https://api.mercury.com/api/v1/accounts"
        accounts_resp = requests.get(accounts_url, headers=headers, timeout=10)
        accounts_resp.raise_for_status()
        accounts_data = accounts_resp.json()
        
        # Mercury API typically returns data in an 'accounts' or 'data' field
        accounts = accounts_data.get('accounts', accounts_data.get('data', [])) if isinstance(accounts_data, dict) else accounts_data

        if not accounts:
            print("No accounts found. Full response:")
            print(accounts_data)
            return
        
        target_account = accounts[0]
        account_id = target_account.get('id')
        print(f"Auditing account: {target_account.get('name')} ({account_id})")

        # 3. Check 'Allow' headers on the transactions endpoint
        transactions_url = f"https://api.mercury.com/api/v1/account/{account_id}/transactions"
        get_resp = requests.get(transactions_url, headers=headers, timeout=10)
        get_resp.raise_for_status()
        
        allow_header = get_resp.headers.get('Allow', 'Not present')
        print(f"Allowed methods (GET response): {allow_header}")

        # 4. Test PATCH on a non-existent resource
        # We use a dummy UUID to avoid messing with real data but trigger the server logic
        dummy_id = "00000000-0000-0000-0000-000000000000"
        patch_url = f"{transactions_url}/{dummy_id}"
        
        print(f"Testing PATCH request on non-existent resource: {patch_url}")
        patch_resp = requests.patch(patch_url, headers=headers, json={"note": "test"}, timeout=10)
        
        print(f"PATCH response status: {patch_resp.status_code}")
        print(f"PATCH response headers: {dict(patch_resp.headers)}")

        # 5. Final Conclusion
        print("\n--- AUDIT SUMMARY ---")
        if "PATCH" in allow_header.upper() or patch_resp.status_code in [405, 403, 401]:
            print("STATUS: Potential PATCH/UPDATE support detected.")
            print("REASON: The server responded to a PATCH attempt (even if it was 404/405/403).")
        else:
            print("STATUS: PATCH support uncertain or not detected.")
            print("REASON: The 'Allow' header did not explicitly list PATCH.")

    except Exception as e:
        print(f"Audit failed: {e}")

if __name__ == "__main__":
    audit_mercury_capabilities()
