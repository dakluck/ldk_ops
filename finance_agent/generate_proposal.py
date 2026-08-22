
import os
from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

def generate_proposal():
    print("🚀 Generating Categorization Proposal...")
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    # 1. Get Categories Mapping
    categories_list = client.get_categories()
    # Map Name -> ID
    name_to_id = {cat['name']: cat['id'] for cat in categories_list}
    
    # 2. Get Transactions
    accounts = client.get_accounts()
    
    proposal_list = []
    
    for account in accounts:
        account_id = account['id']
        transactions = client.get_transactions(account_id)
        
        for tx in transactions:
            desc = tx.get('counterpartyName') or tx.get('bankDescription') or "Unknown"
            
            # Robust category data handling
            category_data = tx.get('categoryData')
            if not category_data:
                current_cat_id = None
                current_cat_name = "None"
            else:
                current_cat_id = category_data.get('id')
                current_cat_name = category_data.get('name', 'None')
            
            # 3. Get Proposed Category Name using the Categorizer
            proposed_cat_name = categorizer.categorize(desc)
            
            # 4. Find the corresponding ID
            proposed_cat_id = name_to_id.get(proposed_cat_name)
            
            # Only add if it's different from the current one
            if proposed_cat_id != current_cat_id:
                # Check for high value
                amount_val = 0
                try:
                    amount_val = abs(float(tx.get('amount', 0)))
                except (TypeError, ValueError):
                    pass
                
                high_value_flag = "⚠️ HIGH VALUE" if amount_val >= 500 else ""
                
                proposal_list.append({
                    "id": tx['id'],
                    "date": tx.get('postedAt', 'N/A'),
                    "desc": desc,
                    "amount": tx.get('amount'),
                    "current": f"{current_cat_name}",
                    "proposed": f"{proposed_cat_name}",
                    "high_value": high_value_flag
                })

    # Output the results
    if not proposal_list:
        print("✅ All transactions are already correctly categorized!")
        return

    print(f"\n✅ Found {len(proposal_list)} transactions needing categorization.\n")
    print(f"{'DATE':<25} | {'DESCRIPTION':<35} | {'AMOUNT':<10} | {'CURRENT':<15} | {'PROPOSED':<20}")
    print("-" * 135)
    
    for p in proposal_list:
        print(f"{str(p['date'])[:25]:<25} | {str(p['desc'])[:35]:<35} | {str(p['amount']):<10} | {p['current']:<15} | {p['proposed']:<20} {p['high_value']}")

if __name__ == "__main__":
    generate_proposal()
