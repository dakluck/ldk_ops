import os
import sys
from datetime import datetime
from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

class FinanceAgentOrchestrator:
    def __init__(self):
        self.client = MercuryClient()
        self.categorizer = TransactionCategorizer()
        self.last_proposals = []

    def run_safe_mode_audit(self):
        """
        Fetches recent transactions and proposes categories without making changes.
        """
        print(f"--- Starting Finance Audit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        
        try:
            accounts = self.client.get_accounts()
            if not accounts:
                print("No accounts found.")
                return

            # For demo/safety, we only look at the first account
            account = accounts[0]
            account_id = account.get('id')
            account_name = account.get('name', 'Unknown Account')
            print(f"Auditing Account: {account_name} ({account_id})")

            transactions = self.client.get_transactions(account_id)
            print(f"DEBUG: Received {len(transactions)} transactions.")

            if not transactions:
                print("No recent transactions found.")
                return

            print(f"\n{'Date':<12} | {'Description':<30} | {'Current':<15} | {'PROPOSED CATEGORY':<15}")
            print("-" * 85)

            self.last_proposals = []

            for tx in transactions:
                if not isinstance(tx, dict):
                    continue
                
                # Use a safe way to handle missing keys. 
                # Mercury uses 'bankDescription' for the primary description.
                date_raw = tx.get('postedAt') or tx.get('date') or 'N/A'
                desc = tx.get('bankDescription') or tx.get('description') or tx.get('counterpartyName', 'Unknown')
                amount = tx.get('amount', 0.0)
                
                # Parse date
                date_str = "N/A"
                if date_raw != 'N/A':
                    try:
                        # Handle ISO format: 2026-07-01T19:04:17.773436Z
                        date_str = datetime.fromisoformat(date_raw.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                        date_str = str(date_raw)[:10]

                # Get proposed category
                proposed_category = self.categorizer.categorize(desc)
                
                # We'll only report if it's not 'Miscellaneous' (to reduce noise)
                if proposed_category != "Miscellaneous":
                    print(f"{date_str:<12} | {desc[:30]:<30} | {amount:<15.2f} | {proposed_category:<15}")
                    self.last_proposals.append({
                        "account_id": account_id,
                        "transaction_id": tx.get('id'),
                        "description": desc,
                        "amount": amount,
                        "proposed_category": proposed_category
                    })
                else:
                    # Still print miscellaneous to show the full picture, but mark it
                    print(f"{date_str:<12} | {desc[:30]:<30} | {amount:<15.2f} | [Misc]")

            if self.last_proposals:
                print(f"\n✅ Found {len(self.last_proposals)} transactions to categorize.")
                print("Ready for 'Write-Back' mode. Type 'apply' to sync these to Mercury.")
            else:
                print("\n✨ All transactions are already categorized or are Miscellaneous.")

        except Exception as e:
            print(f"❌ Audit failed: {e}")

    def apply_proposals(self):
        """
        Applies the pending proposals to the actual Mercury account.
        """
        if not self.last_proposals:
            print("❌ No proposals to apply. Run an audit first.")
            return

        print(f"--- Applying {len(self.last_proposals)} Changes to Mercury ---")
        success_count = 0
        error_count = 0

        for p in self.last_proposals:
            try:
                # Mercury expects a specific format for updates. 
                # We'll update the 'category' or 'note' as a test of write-back.
                # For real tagging, we'd use the specific category field if supported.
                print(f"Updating {p['description']} ({p['transaction_id']})...")
                self.client.update_transaction(p['account_id'], p['transaction_id'], {
                    "note": f"AI Category: {p['proposed_category']}"
                })
                print(f"✅ Success")
                success_count += 1
            except Exception as e:
                print(f"❌ Failed: {e}")
                error_count += 1

        print(f"\nSummary: {success_count} applied, {error_count} failed.")

if __name__ == "__main__":
    # Set CWD to the finance_agent directory so imports work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    orchestrator = FinanceAgentOrchestrator()
    
    while True:
        print("\nCommands: [audit] [apply] [exit]")
        cmd = input(">> ").strip().lower()
        if cmd == 'audit':
            orchestrator.run_safe_mode_audit()
        elif cmd == 'apply':
            orchestrator.apply_proposals()
        elif cmd == 'exit':
            break
        else:
            print("Unknown command.")
