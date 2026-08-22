
from api.mercury_client import MercuryClient

client = MercuryClient()
accounts = client.get_accounts()
if accounts:
    txs = client.get_transactions(accounts[0]['id'])
    if txs:
        print("--- FULL TRANSACTION OBJECT ---")
        import json
        print(json.dumps(txs[0], indent=2))
    else:
        print("No transactions found in first account.")
else:
    print("No accounts found.")
