"""
Year-to-Date Profit & Loss + Balance Sheet from Mercury transactions.
Designed for accountant review — separates operating activity from capital contributions.
"""
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

# Transaction classification
EXCLUDE_PATTERNS = [
    "io autopay", "io payment", "mercury io cashback",
]

FOUNDER_FUNDING = [
    "transfer from another bank",
]

def classify(desc):
    clean = desc.lower().replace("*", " ").replace(";", " ").replace("  ", " ").strip()
    if any(p in clean for p in EXCLUDE_PATTERNS):
        return None, "exclude"
    if any(p in clean for p in FOUNDER_FUNDING):
        return "Founder Funding / Capital Contribution", "capital"
    if "elevations credit union" in clean:
        return "Founder Funding / Capital Contribution", "capital"
    if "account verification" in clean:
        return "Founder Funding / Capital Contribution", "capital"
    return None, None

def generate_full_report():
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    transactions = client.get_transactions()
    print(f"Fetched {len(transactions)} total transactions\n")

    ytd_start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Operating accounts
    operations = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0, "items": []})
    capital = defaultdict(lambda: {"amount": 0.0, "count": 0, "items": []})
    exclude_count = 0

    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        date_raw = tx.get('postedAt') or tx.get('date')
        if not date_raw:
            continue
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except:
            tx_date = None
        if tx_date is None or tx_date < ytd_start:
            continue

        desc = tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amount = float(tx.get('amount', 0))

        cat, tx_type = classify(desc)
        if tx_type == "exclude":
            exclude_count += 1
            continue

        if tx_type == "capital":
            capital[cat]["amount"] += amount
            capital[cat]["count"] += 1
            capital[cat]["items"].append({"date": tx_date.strftime('%Y-%m-%d'), "desc": desc[:50], "amount": amount})
            continue

        category = categorizer.categorize(desc)
        if amount > 0:
            operations[category]["income"] += amount
        else:
            operations[category]["expense"] += abs(amount)
        operations[category]["count"] += 1
        operations[category]["items"].append({"date": tx_date.strftime('%Y-%m-%d'), "desc": desc[:50], "amount": amount})

    # === PRINT REPORT ===
    print("=" * 72)
    print("  LDK INTERNATIONAL, LLC")
    print("  INCOME STATEMENT (Year-to-Date)")
    print(f"  January 1, 2026 through July 16, 2026")
    print("=" * 72)
    print()

    # Revenue
    revenue_total = sum(d["income"] for d in operations.values())
    print("  REVENUE")
    print("  " + "─" * 68)
    for cat, data in sorted(operations.items(), key=lambda x: x[1]["income"], reverse=True):
        if data["income"] > 0:
            print(f"    {cat:<30} ${data['income']:>10,.2f}")
    print(f"  {'Total Revenue':<30} ${revenue_total:>10,.2f}")
    print()

    # Expenses
    expense_total = sum(d["expense"] for d in operations.values())
    print("  EXPENSES — Operating")
    print("  " + "─" * 68)
    for cat, data in sorted(operations.items(), key=lambda x: x[1]["expense"], reverse=True):
        if data["expense"] > 0:
            print(f"    {cat:<30} ${data['expense']:>10,.2f}")
    print(f"  {'Total Operating Expenses':<30} ${expense_total:>10,.2f}")
    print()

    # Net Income (Loss)
    net_income = revenue_total - expense_total
    print("  " + "─" * 68)
    print(f"  {'NET INCOME (LOSS)':<30} ${abs(net_income):>10,.2f}")
    if net_income >= 0:
        print(f"  {'(Profit)':<30}")
    else:
        print(f"  {'(Net Operating Loss)':<30}")
    print("=" * 72)
    print()

    # Balance Sheet — Capital Account
    print("  BALANCE SHEET — EQUITY SECTION")
    print("  " + "─" * 68)
    capital_total = sum(d["amount"] for d in capital.values())
    print(f"    Founder Capital Contributions:     ${capital_total:>10,.2f}")
    print(f"    Retained Earnings (YTD loss):     ${abs(net_income):>10,.2f} ({'credit' if net_income < 0 else 'debit'})")
    print(f"    {'Total Equity':<30} ${capital_total - abs(net_income):>10,.2f}")
    print("  " + "─" * 68)
    print()
    print("  NOTE: Revenue excludes capital contributions from founder.")
    print("        Capital contributions are equity, not operating income.")
    print()

    # Monthly burn
    print("  MONTHLY OPERATING BURN RATE")
    print("  " + "─" * 68)
    monthly_exp = defaultdict(float)
    for cat, data in operations.items():
        for item in data["items"]:
            if item["amount"] < 0:
                month = item["date"][:7]
                monthly_exp[month] += abs(item["amount"])
    for month in sorted(monthly_exp.keys()):
        print(f"    {month:<10} ${monthly_exp[month]:>10,.2f}")
    print(f"    {'Average Monthly Burn':<10} ${sum(monthly_exp.values())/len(monthly_exp) if monthly_exp else 0:>10,.2f}")
    print(f"    {'Cash Runway (at current)':<10} ${capital_total/max(expense_total,1) * 30:>10,.0f} days")
    print("=" * 72)
    print()

    # Runway
    print("  FUNDING STATUS")
    print("  " + "─" * 68)
    total_funded = capital_total
    total_spent = expense_total
    remaining = total_funded - total_spent
    print(f"    Total Capital Invested:   ${total_funded:>10,.2f}")
    print(f"    Total Operating Burn:     ${total_spent:>10,.2f}")
    print(f"    {'Remaining Capital':<18} ${remaining:>10,.2f}")
    if remaining > 0:
        burn_per_month = total_spent / 6.5
        months_remaining = remaining / burn_per_month if burn_per_month > 0 else float('inf')
        print(f"    {'Months of Capital Left':<18} {months_remaining:>9.1f} months")
    else:
        print(f"    {'Status':<18} ALREADY EXCEEDED CAPITAL")
    print("  " + "─" * 68)
    print("=" * 72)

    # Expense details
    print()
    print("  DETAILED EXPENSES")
    print("  " + "─" * 68)
    all_exp = []
    for cat, data in operations.items():
        for item in data["items"]:
            if item["amount"] < 0:
                all_exp.append((cat, item))
    all_exp.sort(key=lambda x: abs(x[1]["amount"]), reverse=True)
    for cat, item in all_exp[:25]:
        print(f"    {item['date']}  {cat:<28} {item['desc']:<30} ${abs(item['amount']):>10,.2f}")
    print("=" * 72)


if __name__ == "__main__":
    generate_full_report()
