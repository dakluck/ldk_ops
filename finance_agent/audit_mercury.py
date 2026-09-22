"""
Mercury Books Audit & Integrity Inspector for LDK International LLC.
Performs a comprehensive health check on Mercury accounts:
- Account balances & connectivity
- Reconciliation & categorization coverage (Books Chart of Accounts)
- Flags any uncategorized or pending transactions needing review
- Receipt policy compliance inspection
- Filters out failed retries
"""
import os
import sys
from pathlib import Path
from collections import Counter

# Set path for relative imports
agent_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(agent_dir))

from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

def run_audit():
    print("=" * 72)
    print("  LDK INTERNATIONAL — MERCURY BOOKS HEALTH & RECONCILIATION AUDIT")
    print("=" * 72)
    
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    try:
        accounts = client.get_accounts()
        if not accounts:
            print("❌ No accounts found.")
            return

        print(f"\n📂 ACCOUNTS OVERVIEW ({len(accounts)} Accounts):")
        total_cash = 0.0
        for acc in accounts:
            bal = float(acc.get('currentBalance', 0.0))
            total_cash += bal
            print(f"  • {acc.get('name', 'Unknown')}: ${bal:,.2f} ({acc.get('status', 'unknown')})")
        print(f"  💰 Total Liquid Cash: ${total_cash:,.2f}")
        
        all_txs = []
        for account in accounts:
            txs = client.get_transactions(account['id'])
            for t in txs:
                t['account_name'] = account.get('name')
            all_txs.extend(txs)
        
        # Categorize by status
        settled_txs = [t for t in all_txs if t.get('status') in ['sent', 'posted', 'completed']]
        pending_txs = [t for t in all_txs if t.get('status') == 'pending']
        failed_txs = [t for t in all_txs if t.get('status') == 'failed']
        
        print("\n📊 TRANSACTION STATUS SUMMARY:")
        print(f"  • Settled / Cleared:  {len(settled_txs)}")
        print(f"  • In-Flight Pending:  {len(pending_txs)}")
        print(f"  • Excluded (Failed):  {len(failed_txs)}")
        print(f"  • Total Ledger Items: {len(all_txs)}")

        # Check Active Items (Settled + Pending)
        active_txs = settled_txs + pending_txs
        uncategorized = []
        categorized_counts = Counter()
        missing_receipts = []

        for t in active_txs:
            cat_data = t.get('categoryData')
            cat_name = cat_data.get('name') if cat_data else None
            desc = t.get('counterpartyName') or t.get('bankDescription') or 'Unknown'
            amt = float(t.get('amount', 0))
            
            if cat_name:
                categorized_counts[cat_name] += 1
            else:
                suggested = categorizer.categorize(desc)
                uncategorized.append({
                    "id": t.get('id'),
                    "date": t.get('postedAt') or t.get('createdAt'),
                    "desc": desc,
                    "amount": amt,
                    "status": t.get('status'),
                    "suggested": suggested,
                    "note": t.get('note')
                })

            if t.get('compliantWithReceiptPolicy') is False:
                missing_receipts.append(t)

        print("\n🏷️  MERCURY BOOKS CATEGORY DISTRIBUTION:")
        if categorized_counts:
            for cat, count in categorized_counts.most_common():
                print(f"  • {cat:<32} {count:>3} txn(s)")
        else:
            print("  (No categorized transactions yet)")

        if uncategorized:
            print(f"\n⚠️  ACTION REQUIRED: {len(uncategorized)} UNCATEGORIZED ACTIVE TRANSACTION(S):")
            print("  " + "─" * 70)
            for u in uncategorized:
                status_str = f"[{u['status'].upper()}]"
                date_str = str(u['date'])[:10] if u['date'] else "N/A"
                print(f"  {date_str} | {status_str:<9} | {u['desc'][:25]:<25} | ${u['amount']:>8.2f}")
                print(f"    ↳ Suggested Books Category: {u['suggested']}")
                if u['note']:
                    print(f"    ↳ Memo/Note: {u['note']}")
            print("  " + "─" * 70)
        else:
            print("\n✅ All active transactions are fully categorized in Mercury Books!")

        print("\n🧾 RECEIPT POLICY COMPLIANCE:")
        if missing_receipts:
            print(f"  ⚠️  {len(missing_receipts)} transaction(s) require receipt upload.")
        else:
            print("  ✓ 100% compliant with receipt policies.")

        print("\n" + "=" * 72)
        print("✅ AUDIT COMPLETE")
        print("=" * 72)

    except Exception as e:
        print(f"❌ ERROR during audit: {str(e)}")


if __name__ == "__main__":
    run_audit()
