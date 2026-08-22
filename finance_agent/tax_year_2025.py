"""
Fetch all Mercury transactions for Tax Year 2025 (Jan 1 - Dec 31)
and produce income/expense summary.
"""
import os, sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.mercury_client import MercuryClient

TAX_YEAR = 2025
FROM_DATE = f"{TAX_YEAR}-01-01"
TO_DATE = f"{TAX_YEAR}-12-31"

def categorize(desc):
    p = desc.lower() if desc else ""
    
    # Marketing & Advertising — check before generic "google"
    if any(x in p for x in ["google ads", "google ad", "google*ads", "google *ads", "facebook ads", "meta ads", "linkedin ads", "adobe stock", "unsplash", "shutterstock", "stock photo", "stock image", "sponsor"]):
        return "Marketing & Advertising"
    
    # Software & Subscriptions
    if "github" in p:
        return "Software & Subscriptions"
    if any(x in p for x in ["office 365", "microsoft 365"]):
        return "Software & Subscriptions"
    # Google Workspace — flexible matching for "GOOGLE *WORKSPACE_LDK-" etc
    if "workspace" in p and "google" in p:
        return "Software & Subscriptions"
    
    # Infrastructure — cloud, hosting, dev tools
    if any(x in p for x in ["google cloud", "google*cloud", "google *cloud", "aws", "heroku", "vercel", "netlify", "datadog", "sentry", "cloudflare", "claude", "anthropic"]):
        return "Infrastructure"
    
    # Meals & Entertainment
    if any(x in p for x in ["starbucks", "restaurants", "restaurant", "door dash", "ubereats", "grubhub", "seamless"]):
        return "Meals & Entertainment"
    
    # Travel
    if any(x in p for x in ["uber ", "uber," "lyft", "taxi", "airline", "hotel", "airbnb"]):
        return "Travel"
    
    # Business/registration
    if "zenbusiness" in p:
        return "Professional Services"
    
    # Miscellaneous
    if any(x in p for x in ["itch.io", "itch.io - game store"]):
        return "Miscellaneous"
    
    return "Miscellaneous"

def is_transfer(desc, amount):
    p = desc.lower() if desc else ""
    # IO Autopay / IO Payment / external transfers are transfers, not expenses
    if any(x in p for x in ["io autopay", "io payment", "elevations credit union", "transfer from"]):
        return True
    return False

def is_income(desc, amount):
    p = desc.lower() if desc else ""
    if amount > 0:
        if any(x in p for x in ["deposit", "payment received", "payment from", "wire from", "transfer in", "incoming", "cashback", "refund"]):
            return True
    return False

def classify(desc, amount):
    """Return ('income', cat), ('expense', cat), or ('transfer', None)."""
    if is_transfer(desc, amount):
        return 'transfer', None
    if amount > 0 and is_income(desc, amount):
        return 'income', categorize(desc)
    if amount < 0:
        return 'expense', categorize(desc)
    return 'transfer', None

def main():
    print(f"Mercury Tax Year {TAX_YEAR} Report")
    print(f"Period: {FROM_DATE} to {TO_DATE}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    client = MercuryClient()
    accounts = client.get_accounts()

    # Fetch ALL transactions (no account filter - API has a bug)
    data = client._request("GET", "transactions")
    all_txns = data.get("transactions", data.get("data", []))

    # Deduplicate by ID
    seen = set()
    unique_txns = []
    for t in all_txns:
        tid = t.get('id')
        if tid and tid not in seen:
            seen.add(tid)
            unique_txns.append(t)

    print(f"Total unique transactions fetched: {len(unique_txns)}")

    # Filter by date range using createdAt or postedAt
    ytd_txns = []
    for tx in unique_txns:
        date_raw = tx.get('createdAt') or tx.get('postedAt')
        if not date_raw:
            continue
        try:
            d = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
            if d.year == TAX_YEAR:
                ytd_txns.append(tx)
        except:
            pass

    print(f"Transactions in Tax Year {TAX_YEAR}: {len(ytd_txns)}")

    if not ytd_txns:
        # Show what years ARE available
        all_dates = set()
        for tx in unique_txns:
            d = tx.get('createdAt') or tx.get('postedAt')
            if d:
                try:
                    all_dates.add(datetime.fromisoformat(d.replace('Z', '+00:00')).year)
                except:
                    pass
        print(f"\n  ⚠️  No {TAX_YEAR} transactions found.")
        print(f"  Available transaction years: {sorted(all_dates)}")
        
        # Show 2026 summary as fallback
        ytd_txns = [tx for tx in unique_txns
                    if tx.get('createdAt') and tx['createdAt'].startswith('2026')]
        if ytd_txns:
            print(f"\n  Showing {TAX_YEAR+1} transactions instead ({len(ytd_txns)} total):")
            
            for tx in ytd_txns:
                date_raw = tx.get('createdAt') or tx.get('postedAt') or 'N/A'
                date_str = str(date_raw)[:10] if date_raw != 'N/A' else 'N/A'
                desc = tx.get('bankDescription') or tx.get('counterpartyName') or 'Unknown'
                amount = tx.get('amount', 0)
                try:
                    amount = float(amount)
                except:
                    amount = 0
                
                kind, cat = classify(desc, amount)
                if kind == 'income':
                    print(f"  INCOME:  {date_str}  {desc[:40]:<40} +${amount:,.2f} ({cat})")
                elif kind == 'expense':
                    print(f"  EXPENSE: {date_str}  {desc[:40]:<40} ${abs(amount):,.2f} ({cat})")
                else:
                    print(f"  TRANSFER:{date_str}  {desc[:40]:<40} ${abs(amount):,.2f}")
        
        return

    # Use Mercury's built-in categories when available
    def get_category(tx):
        cat = tx.get('categoryData', {}).get('name', '').lower()
        if cat:
            return cat
        _, cat = classify(tx.get('bankDescription') or tx.get('counterpartyName') or '', 0)
        return cat or "Miscellaneous"

    # Process income and expenses
    income_txns = []
    expense_txns = []
    transfer_txns = []
    cat_totals = defaultdict(float)

    for tx in ytd_txns:
        date_raw = tx.get('createdAt') or tx.get('postedAt') or ''
        desc = tx.get('bankDescription') or tx.get('counterpartyName') or 'Unknown'
        amount = tx.get('amount', 0)
        try:
            amount = float(amount)
        except:
            amount = 0
        
        date_str = str(date_raw)[:10]
        cat = get_category(tx)
        kind, cat2 = classify(desc, amount)
        final_cat = cat2 or cat
        
        if kind == 'income':
            income_txns.append({'date': date_str, 'desc': desc, 'amount': amount, 'cat': final_cat, 'acct': tx.get('accountId','')})
        elif kind == 'expense':
            expense_txns.append({'date': date_str, 'desc': desc, 'amount': abs(amount), 'cat': final_cat, 'acct': tx.get('accountId','')})
            cat_totals[final_cat] += abs(amount)
        else:
            transfer_txns.append({'date': date_str, 'desc': desc, 'amount': amount, 'acct': tx.get('accountId','')})

    total_income = sum(t['amount'] for t in income_txns)
    total_expense = sum(t['amount'] for t in expense_txns)

    # Account name lookup
    acct_map = {a.get('id'): a.get('name','') for a in accounts}
    acct_map['15cbcfb8-fc9d-11f0-aba4-ebc377832f02'] = 'External (Elevations CU / IO)'

    print(f"\n{'='*60}")
    print(f"  TAX YEAR {TAX_YEAR} — SUMMARY")
    print(f"{'='*60}")
    print(f"  Total Income:   ${total_income:>15,.2f}  ({len(income_txns)} txns)")
    print(f"  Total Expenses: ${total_expense:>15,.2f}  ({len(expense_txns)} txns)")
    print(f"  Total Transfers: ${sum(abs(t['amount']) for t in transfer_txns):>11,.2f}  ({len(transfer_txns)} txns)")
    print(f"  Net (excl. transfers): ${total_income - total_expense:>11,.2f}")

    print(f"\n  Expenses by Category:")
    for cat in sorted(cat_totals, key=cat_totals.get, reverse=True):
        if cat_totals[cat] > 0:
            print(f"    {cat:<28} ${cat_totals[cat]:>12,.2f}")

    if income_txns:
        print(f"\n  Income ({len(income_txns)} transactions):")
        for t in sorted(income_txns, key=lambda x: x['date'], reverse=True):
            acct = acct_map.get(t.get('acct',''), '')
            print(f"    {t['date']}  {acct[:20]:<20} +${t['amount']:>10,.2f}  {t['desc'][:40]}")

    print(f"\n  Expenses ({len(expense_txns)} transactions):")
    for t in sorted(expense_txns, key=lambda x: x['date'], reverse=True):
        acct = acct_map.get(t.get('acct',''), '')
        print(f"    {t['date']}  {acct[:20]:<20} ${t['amount']:>10,.2f}  {t['desc'][:40]}")

    if transfer_txns:
        print(f"\n  Transfers ({len(transfer_txns)} transactions):")
        for t in sorted(transfer_txns, key=lambda x: x['date'], reverse=True):
            acct = acct_map.get(t.get('acct',''), '')
            print(f"    {t['date']}  {acct[:20]:<20} ${abs(t['amount']):>10,.2f}  {t['desc'][:40]}")

    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
