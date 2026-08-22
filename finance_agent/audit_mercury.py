
import os
from api.mercury_client import MercuryClient

def run_audit():
    print("🚀 Starting Programmatic Mercury Audit...")
    
    client = MercuryClient()
    
    try:
        # 1. Get Accounts
        accounts = client.get_accounts()
        if not accounts:
            print("❌ No accounts found.")
            return

        print(f"✅ Found {len(accounts)} accounts.")
        
        all_transactions = []
        
        for account in accounts:
            account_id = account['id']
            account_name = account.get('name', 'Unknown Account')
            print(f"🔍 Fetching transactions for: {account_name} ({account_id})...")
            
            transactions = client.get_transactions(account_id)
            all_transactions.extend(transactions)
            print(f"   Found {len(transactions)} transactions.")

        print(f"\n✅ Audit Complete. Total transactions retrieved: {len(all_transactions)}")
        
        if all_transactions:
            print("\n--- SAMPLE TRANSACTIONS (First 5) ---")
            for tx in all_transactions[:5]:
                            print(f"ID: {tx.get('id')} | Date: {tx.get('postedAt')} | Desc: {tx.get('counterpartyName')} | Amt: {tx.get('amount')} | CurrCat: {tx.get('categoryData', {}).get('name') if tx.get('categoryData') else 'None'}")
            print("\n--- END SAMPLE ---")
        else:
            print("⚠️ No transactions found in any account.")

    except Exception as e:
        print(f"❌ ERROR during audit: {str(e)}")

if __name__ == "__main__":
    run_audit()
