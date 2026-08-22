
import os
from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

def apply_categorization():
    print("🚀 Starting Mercury Transaction Categorization Sync...")
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    # 1. Get Categories Mapping (Name -> ID)
    categories_list = client.get_categories()
    name_to_id = {cat['name']: cat['id'] for cat in categories_list}
    
    # 2. Get Accounts
    accounts = client.get_accounts()
    
    summary = {
        "total_scanned": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "total_failed": 0,
        "high_value_found": []
    }

    print(f"Found {len(accounts)} accounts to process.\n")

    for account in accounts:
        account_id = account['id']
        account_name = account.get('name', 'Unknown Account')
        print(f"📂 Processing Account: {account_name} ({account_id})")
        
        transactions = client.get_transactions(account_id)
        summary["total_scanned"] += len(transactions)
        
        for tx in transactions:
            tx_id = tx['id']
            desc = tx.get('counterpartyName') or tx.get('bankDescription') or "Unknown"
            amount = tx.get('amount', 0)
            
            # Robust amount check for high-value
            try:
                abs_amount = abs(float(amount))
            except (TypeError, ValueError):
                abs_amount = 0

            # Robust category data handling
            category_data = tx.get('categoryData')
            if not category_data:
                current_cat_id = None
                current_cat_name = "None"
            else:
                current_cat_id = category_data.get('id')
                current_cat_name = category_data.get('name', 'None')

            # 3. Get Proposed Category Name
            proposed_cat_name = categorizer.categorize(desc)
            
            # 4. Find the corresponding ID
            proposed_cat_id = name_to_id.get(proposed_cat_name)

            # Check if update is needed
            if proposed_cat_id and proposed_cat_id != current_cat_id:
                # Check for high value
                if abs_amount >= 500:
                    summary["high_value_found"].append({
                        "id": tx_id,
                        "desc": desc,
                        "amount": amount,
                        "proposed": proposed_cat_name
                    })
                    # We still proceed but we will report it.
                    # Given the user said "Apply all", we proceed.

                try:
                    print(f"  🔄 Updating: {desc} ({amount}) | {current_cat_name} ➡️ {proposed_cat_name}")
                    client.update_transaction(account_id, tx_id, {"categoryId": proposed_cat_id})
                    summary["total_updated"] += 1
                except Exception as e:
                    print(f"  ❌ Failed to update {tx_id}: {e}")
                    summary["total_failed"] += 1
            else:
                summary["total_skipped"] += 1

    # Final Summary Report
    print("\n" + "="*40)
    print("✅ SYNC COMPLETE")
    print("="*40)
    print(f"Total Transactions Scanned: {summary['total_scanned']}")
    print(f"Successfully Updated:      {summary['total_updated']}")
    print(f"Skipped (Correct):       {summary['total_skipped']}")
    print(f"Failed:                   {summary['total_failed']}")
    
    if summary["high_value_found"]:
        print("\n⚠️  HIGH-VALUE TRANSACTIONS PROCESSED:")
        for hv in summary["high_value_found"]:
            print(f"  - {hv['desc']} ({hv['amount']}) ➡️ {hv['proposed']}")
    print("="*40)

if __name__ == "__main__":
    apply_categorization()
