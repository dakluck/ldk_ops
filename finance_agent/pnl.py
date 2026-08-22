"""
Year-to-Date Profit & Loss from Mercury transactions.
Runs a categorization audit and aggregates by category.
Excludes internal transfers (IO payments, bank transfers, cashback).
"""
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

# Set CWD to finance_agent directory so imports work
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

# Patterns that indicate circular/internal transactions to exclude
TRANSFER_PATTERNS_EXCLUDE = [
    "io autopay",
    "io payment",
    "mercury io cashback",
]

# Patterns that are founder funding (capital contributions) - keep as income
FOUNDER_FUNDING = [
    "transfer from another bank",
]

def classify_special(desc):
    """Classify special non-business-categorization transactions."""
    clean = desc.lower().replace("*", " ").replace(";", " ").replace("  ", " ").strip()
    
    # Exclude circular movements
    if any(p in clean for p in TRANSFER_PATTERNS_EXCLUDE):
        return None, "exclude"
    
    # Founder funding / capital contributions
    if any(p in clean for p in FOUNDER_FUNDING):
        return "Founder Funding", "income"
    
    # One-time things
    if "elevations credit union" in clean:
        return "Founder Funding", "income"  # Likely personal deposit
    
    if "account verification" in clean:
        return "Founder Funding", "income"  # Bank account verification deposit
    
    return None, None

def generate_pnl():
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    # Get all transactions
    transactions = client.get_transactions()
    print(f"Total transactions fetched: {len(transactions)}")
    print()
    
    # YTD: Jan 1, 2026 to now
    ytd_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    
    # Category buckets
    categories = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0, "items": []})
    
    filtered_out = 0  # Count of internal transfers excluded
    total_items = 0   # Running count of processed transactions
    
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        
        # Parse date
        date_raw = tx.get('postedAt') or tx.get('date')
        if not date_raw:
            continue
        
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except:
            tx_date = None
        
        # Skip if before 2026 or no date
        if tx_date is None or tx_date < ytd_start:
            continue
        
        desc = tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amount = float(tx.get('amount', 0))
        
        # Check if this is a special-classified transaction
        special_category, special_type = classify_special(desc)
        
        if special_type == "exclude":
            filtered_out += 1
            continue
        
        if special_type == "income":
            categories[special_category]["income"] += amount
            categories[special_category]["count"] += 1
            categories[special_category]["items"].append({
                "date": tx_date.strftime('%Y-%m-%d'),
                "desc": desc[:50],
                "amount": amount
            })
            total_items += 1
            continue
        
        # Standard categorization
        category = categorizer.categorize(desc)
        
        if amount > 0:
            categories[category]["income"] += amount
        else:
            categories[category]["expense"] += abs(amount)
        
        categories[category]["count"] += 1
        categories[category]["items"].append({
            "date": tx_date.strftime('%Y-%m-%d'),
            "desc": desc[:50],
            "amount": amount
        })
        total_items += 1
    
    # Print P&L
    print("=" * 72)
    print("  LDK INTERNATIONAL — YEAR-TO-DATE P&L (2026)")
    print(f"  Period: 2026-01-01 to {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    print("=" * 72)
    print()
    
    total_income = 0.0
    total_expense = 0.0
    
    # Sort categories by total (absolute) value, descending
    sorted_cats = sorted(categories.items(), key=lambda x: abs(x[1]["income"] - x[1]["expense"]), reverse=True)
    
    for cat, data in sorted_cats:
        net = data["income"] - data["expense"]
        if data["count"] == 0:
            continue
        
        if net >= 0:
            bar = "▲"
        else:
            bar = "▼"
        
        print(f"  {cat}")
        print(f"    Income:  ${data['income']:>10,.2f}")
        print(f"    Expense: ${data['expense']:>10,.2f}")
        print(f"    Net:     ${abs(net):>10,.2f} {bar} ({data['count']} txns)")
        print()
    
    total_income = sum(d["income"] for d in categories.values())
    total_expense = sum(d["expense"] for d in categories.values())
    net_profit = total_income - total_expense
    
    print("=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    print(f"  Total Income:  ${total_income:>10,.2f}")
    print(f"  Total Expense: ${total_expense:>10,.2f}")
    print(f"  Net Profit:    ${abs(net_profit):>10,.2f}")
    print(f"  {'▲ Profit' if net_profit >= 0 else '▼ Loss'}")
    print(f"  Margin:        {(net_profit/total_income*100 if total_income > 0 else 0):>9.1f}%")
    print(f"  Transactions:  {total_items:>10,} (excluded {filtered_out} transfers)")
    print("=" * 72)
    
    # Monthly breakdown
    print()
    print("  MONTHLY BREAKDOWN")
    print("-" * 72)
    
    monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for cat, data in categories.items():
        for item in data["items"]:
            month = item["date"][:7]  # YYYY-MM
            amt = item["amount"]
            if amt > 0:
                monthly[month]["income"] += amt
            else:
                monthly[month]["expense"] += abs(amt)
    
    print(f"  {'Month':<10} {'Income':>12} {'Expense':>12} {'Net':>12}")
    print(f"  {'─'*10} {'─'*12} {'─'*12} {'─'*12}")
    
    month_total_income = 0
    month_total_expense = 0
    for month in sorted(monthly.keys()):
        inc = monthly[month]["income"]
        exp = monthly[month]["expense"]
        net = inc - exp
        month_total_income += inc
        month_total_expense += exp
        marker = "▲" if net >= 0 else "▼"
        print(f"  {month:<10} ${inc:>10,.2f} ${exp:>10,.2f} ${abs(net):>9,.2f} {marker}")
    
    print(f"  {'─'*10} {'─'*12} {'─'*12} {'─'*12}")
    print(f"  YTD Total:  ${month_total_income:>10,.2f} ${month_total_expense:>10,.2f} ${abs(month_total_income - month_total_expense):>9,.2f}")
    print("=" * 72)
    
    # Expense deep-dive by sub-category
    print()
    print("  TOP EXPENSES (all time)")
    print("-" * 72)
    
    all_expenses = []
    for cat, data in categories.items():
        for item in data["items"]:
            if item["amount"] < 0:
                all_expenses.append((cat, item))
    
    all_expenses.sort(key=lambda x: abs(x[1]["amount"]), reverse=True)
    
    for cat, item in all_expenses[:20]:
        print(f"  {item['date']} | {cat:<30} | {item['desc']:<30} | ${abs(item['amount']):>10,.2f}")
    
    print("=" * 72)
    
    # Revenue deep-dive
    print()
    print("  ALL INCOME ITEMS")
    print("-" * 72)
    
    all_income = []
    for cat, data in categories.items():
        for item in data["items"]:
            if item["amount"] > 0:
                all_income.append((cat, item))
    
    all_income.sort(key=lambda x: x[1]["amount"], reverse=True)
    
    for cat, item in all_income[:20]:
        print(f"  {item['date']} | {cat:<30} | {item['desc']:<30} | ${abs(item['amount']):>10,.2f}")
    
    print("=" * 72)
    
    # Annualized run-rate
    if total_items > 0:
        days_in_ytd = (datetime.now(timezone.utc).date() - datetime(2026, 1, 1).date()).days
        if days_in_ytd > 0:
            run_rate_monthly = net_profit / days_in_ytd * 30
            run_rate_annual = net_profit / days_in_ytd * 365
            print()
            print("  RUN-RATE (annualized from YTD)")
            print("-" * 72)
            print(f"  Daily Net:       ${net_profit / days_in_ytd:>10,.2f}")
            print(f"  Monthly Run-rate: ${run_rate_monthly:>10,.2f}")
            print(f"  Annual Run-rate:  ${run_rate_annual:>10,.2f}")
            print("=" * 72)


if __name__ == "__main__":
    generate_pnl()
