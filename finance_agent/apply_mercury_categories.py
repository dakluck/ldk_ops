"""
Mercury Transaction Categorization Sync (Dry-Run by default).
Safely suggests or applies categories for uncategorized transactions.
Defers to existing categories in Mercury Books and strictly excludes failed billing retries.
Usage:
  python3 apply_mercury_categories.py          # Dry-run audit (read-only)
  python3 apply_mercury_categories.py --apply  # Push category updates to Mercury API
"""
import os
import sys
import argparse
from pathlib import Path

agent_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(agent_dir))

from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

def apply_categorization(dry_run: bool = True):
    mode_str = "DRY-RUN (Audit Only)" if dry_run else "LIVE APPLY"
    print(f"🚀 Starting Mercury Transaction Categorization [{mode_str}]...")
    
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    # 1. Get Categories Mapping (Name -> ID)
    categories_list = client.get_categories()
    name_to_id = {cat['name']: cat['id'] for cat in categories_list}
    
    # 2. Get Accounts
    accounts = client.get_accounts()
    
    summary = {
        "total_scanned": 0,
        "already_categorized": 0,
        "failed_retries_skipped": 0,
        "proposed_updates": 0,
        "successfully_applied": 0,
        "failed_updates": 0,
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
            status = tx.get('status')
            
            # Skip failed transactions (e.g. failed billing retries)
            if status == 'failed':
                summary["failed_retries_skipped"] += 1
                continue

            desc = tx.get('counterpartyName') or tx.get('bankDescription') or "Unknown"
            amount = tx.get('amount', 0)
            
            try:
                abs_amount = abs(float(amount))
            except (TypeError, ValueError):
                abs_amount = 0

            category_data = tx.get('categoryData')
            current_cat_id = category_data.get('id') if category_data else None
            current_cat_name = category_data.get('name', 'None') if category_data else 'None'

            # Defer to Mercury Books: if already categorized, don't overwrite
            if current_cat_id:
                summary["already_categorized"] += 1
                continue

            # Get Proposed Category Name
            proposed_cat_name = categorizer.categorize(desc)
            proposed_cat_id = name_to_id.get(proposed_cat_name)

            if proposed_cat_id:
                summary["proposed_updates"] += 1
                if abs_amount >= 500:
                    summary["high_value_found"].append({
                        "id": tx_id,
                        "desc": desc,
                        "amount": amount,
                        "proposed": proposed_cat_name
                    })

                if not dry_run:
                    try:
                        print(f"  🔄 Updating: {desc} (${amount}) | {current_cat_name} ➡️ {proposed_cat_name}")
                        client.update_transaction(account_id, tx_id, {"categoryId": proposed_cat_id})
                        summary["successfully_applied"] += 1
                    except Exception as e:
                        print(f"  ❌ Failed to update {tx_id}: {e}")
                        summary["failed_updates"] += 1
                else:
                    print(f"  🔍 [Dry-Run] Suggest: {desc} (${amount}) ➡️ {proposed_cat_name}")

    # Final Summary Report
    print("\n" + "=" * 48)
    print(f"✅ SYNC SUMMARY [{mode_str}]")
    print("=" * 48)
    print(f"Total Transactions Scanned:    {summary['total_scanned']}")
    print(f"Failed Retries Excluded:       {summary['failed_retries_skipped']}")
    print(f"Already Categorized in Books:  {summary['already_categorized']}")
    print(f"Proposed Categorizations:      {summary['proposed_updates']}")
    if not dry_run:
        print(f"Successfully Applied:          {summary['successfully_applied']}")
        print(f"Failed Updates:                {summary['failed_updates']}")
    
    if summary["high_value_found"]:
        print("\n⚠️  HIGH-VALUE TRANSACTIONS PROCESSED (≥ $500):")
        for hv in summary["high_value_found"]:
            print(f"  • {hv['desc']} (${hv['amount']}) ➡️ {hv['proposed']}")
    print("=" * 48)
    if dry_run and summary['proposed_updates'] > 0:
        print("💡 Note: Run with `--apply` to commit these suggestions to Mercury.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mercury Transaction Categorization Sync")
    parser.add_argument("--apply", action="store_true", help="Apply updates to Mercury API (defaults to dry-run)")
    args = parser.parse_args()
    
    apply_categorization(dry_run=not args.apply)
