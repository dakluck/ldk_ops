"""
Monthly Financial Report for LDK International.
Fetches Mercury transactions for the current month and produces:
- Key financial metrics (income, expenses, net)
- Category breakdown
- Anomaly detection (unusual amounts, repeated small charges)
"""
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict
from statistics import median

_reports_dir = os.path.dirname(os.path.abspath(__file__))
_agent_dir = os.path.dirname(_reports_dir)
sys.path.insert(0, _agent_dir)
os.chdir(_agent_dir)

from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

# Transaction classification patterns
TRANSFER_PATTERNS_EXCLUDE = [
    "io autopay", "io payment", "mercury io cashback",
]

FOUNDER_FUNDING = [
    "transfer from another bank",
]


def classify_special(desc):
    """Classify special non-business-categorization transactions."""
    clean = desc.lower().replace("*", " ").replace(";", " ").replace("  ", " ").strip()
    
    if any(p in clean for p in TRANSFER_PATTERNS_EXCLUDE):
        return None, "exclude"
    
    if any(p in clean for p in FOUNDER_FUNDING):
        return "Founder Funding / Capital Contribution", "capital"
    
    if "elevations credit union" in clean:
        return "Founder Funding / Capital Contribution", "capital"
    
    if "account verification" in clean:
        return "Founder Funding / Capital Contribution", "capital"
    
    return None, None


def detect_anomalies(category_transactions):
    """
    Detect anomalies in transaction amounts within a category.
    Uses IQR method: anything > Q3 + 1.5*IQR or < Q1 - 1.5*IQR is anomalous.
    Also flags single transactions that are orders of magnitude different.
    """
    anomalies = []
    
    for cat, txns in category_transactions.items():
        if len(txns) < 2:
            # Single transaction can't establish a baseline, but flag very large ones
            for t in txns:
                if abs(t['amount']) > 10000:
                    anomalies.append({
                        'type': 'large_single',
                        'category': cat,
                        'description': t['desc'],
                        'date': t['date'],
                        'amount': abs(t['amount']),
                        'reason': f'Large single transaction (${abs(t["amount"]):,.2f})'
                    })
            continue
        
        amounts = [abs(t['amount']) for t in txns]
        sorted_amounts = sorted(amounts)
        n = len(sorted_amounts)
        q1 = sorted_amounts[n // 4]
        q3 = sorted_amounts[3 * n // 4]
        iqr = q3 - q1
        
        upper_bound = q3 + 1.5 * iqr if iqr > 0 else q3 * 2
        lower_bound = max(0, q1 - 1.5 * iqr)
        
        for t in txns:
            amt = abs(t['amount'])
            if amt > upper_bound:
                anomalies.append({
                    'type': 'outlier_high',
                    'category': cat,
                    'description': t['desc'],
                    'date': t['date'],
                    'amount': amt,
                    'reason': f'Above 75th percentile + 1.5*IQR (upper bound: ${upper_bound:,.2f})'
                })
            elif amt < lower_bound and amt > 0 and iqr > 0:
                anomalies.append({
                    'type': 'outlier_low',
                    'category': cat,
                    'description': t['desc'],
                    'date': t['date'],
                    'amount': amt,
                    'reason': f'Below 25th percentile - 1.5*IQR (lower bound: ${lower_bound:,.2f})'
                })
    
    return anomalies


def generate_monthly_report():
    """Generate a comprehensive monthly financial report."""
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    # Fetch all transactions
    transactions = client.get_transactions()
    print(f"Total transactions fetched: {len(transactions)}")
    print()
    
    # Determine the current month
    now = datetime.now(timezone.utc)
    current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        current_month_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        current_month_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    
    month_label = now.strftime("%B %Y")
    
    print("=" * 72)
    print(f"  LDK INTERNATIONAL — MONTHLY FINANCIAL REPORT")
    print(f"  Period: {current_month_start.strftime('%B %Y')}")
    print("=" * 72)
    print()
    
    # Filter for current month
    month_transactions = []
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        
        date_raw = tx.get('postedAt') or tx.get('date')
        if not date_raw:
            continue
        
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except:
            continue
        
        if tx_date < current_month_start or tx_date >= current_month_end:
            continue
        
        month_transactions.append(tx)
    
    print(f"Transactions in {month_label}: {len(month_transactions)}")
    print()
    
    # Categorize transactions
    categories = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0, "items": []})
    filtered_out = 0
    total_items = 0
    
    category_transactions = defaultdict(list)  # For anomaly detection
    
    for tx in month_transactions:
        desc = tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amount = float(tx.get('amount', 0))
        date_raw = tx.get('postedAt') or tx.get('date')
        tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00')) if date_raw else now
        
        # Check for special classification
        special_category, special_type = classify_special(desc)
        
        if special_type == "exclude":
            filtered_out += 1
            continue
        
        if special_type == "capital":
            categories[special_category]["income"] += amount
            categories[special_category]["count"] += 1
            item = {
                "date": tx_date.strftime('%Y-%m-%d'),
                "desc": desc[:50],
                "amount": amount
            }
            categories[special_category]["items"].append(item)
            category_transactions[special_category].append(item)
            total_items += 1
            continue
        
        # Standard categorization
        category = categorizer.categorize(desc)
        
        if amount > 0:
            categories[category]["income"] += amount
        else:
            categories[category]["expense"] += abs(amount)
        
        categories[category]["count"] += 1
        item = {
            "date": tx_date.strftime('%Y-%m-%d'),
            "desc": desc[:50],
            "amount": amount
        }
        categories[category]["items"].append(item)
        category_transactions[category].append(item)
        total_items += 1
    
    # Calculate totals
    total_income = sum(d["income"] for d in categories.values())
    total_expense = sum(d["expense"] for d in categories.values())
    net_profit = total_income - total_expense
    
    # === PRINT CATEGORY BREAKDOWN ===
    print("  REVENUE & EXPENSES BY CATEGORY")
    print("  " + "─" * 68)
    
    sorted_cats = sorted(categories.items(), key=lambda x: abs(x[1]["income"] - x[1]["expense"]), reverse=True)
    
    for cat, data in sorted_cats:
        if data["count"] == 0:
            continue
        
        net = data["income"] - data["expense"]
        if data["income"] > 0:
            print(f"\n  {cat}")
            print(f"    Income:     ${data['income']:>10,.2f}  ({data['count']} transactions)")
            if data["expense"] > 0:
                print(f"    Expenses:   ${data['expense']:>10,.2f}")
        else:
            print(f"\n  {cat}")
            print(f"    Expenses:   ${data['expense']:>10,.2f}  ({data['count']} transactions)")
        
        if net >= 0:
            print(f"    Net:        ${abs(net):>10,.2f} ▲")
        else:
            print(f"    Net:        ${abs(net):>10,.2f} ▼")
    
    print()
    print("  " + "─" * 68)
    print(f"\n  SUMMARY")
    print(f"  " + "─" * 68)
    print(f"  Total Income:     ${total_income:>10,.2f}")
    print(f"  Total Expenses:   ${total_expense:>10,.2f}")
    print(f"  Net (Income - Expenses): ${net_profit:>10,.2f}")
    if net_profit >= 0:
        print(f"  Status:           PROFIT")
    else:
        print(f"  Status:           LOSS")
    
    if total_income > 0:
        margin = net_profit / total_income * 100
        print(f"  Profit Margin:    {margin:>9.1f}%")
    
    print(f"  Transactions:     {total_items:>10,} (excluded {filtered_out} transfers)")
    print()
    
    # === TOP EXPENSES ===
    print("  TOP 20 EXPENSES")
    print("  " + "─" * 68)
    
    all_expenses = []
    for cat, data in categories.items():
        for item in data["items"]:
            if item["amount"] < 0:
                all_expenses.append((cat, item))
    
    all_expenses.sort(key=lambda x: abs(x[1]["amount"]), reverse=True)
    
    for cat, item in all_expenses[:20]:
        print(f"  {item['date']} | {cat:<30} | {item['desc']:<30} | ${abs(item['amount']):>10,.2f}")
    
    print()
    
    # === ALL INCOME ITEMS ===
    if total_income > 0:
        print("  ALL INCOME ITEMS")
        print("  " + "─" * 68)
        
        all_income = []
        for cat, data in categories.items():
            for item in data["items"]:
                if item["amount"] > 0:
                    all_income.append((cat, item))
        
        all_income.sort(key=lambda x: x[1]["amount"], reverse=True)
        
        for cat, item in all_income:
            print(f"  {item['date']} | {cat:<30} | {item['desc']:<30} | ${item['amount']:>10,.2f}")
        
        print()
    
    # === ANOMALY DETECTION ===
    print("  ANOMALY DETECTION")
    print("  " + "─" * 68)
    
    anomalies = detect_anomalies(category_transactions)
    
    if anomalies:
        print(f"\n  ⚠️  Found {len(anomalies)} potential anomalies:\n")
        
        for anomaly in anomalies:
            print(f"  [{anomaly['type'].upper()}] {anomaly['date']} | {anomaly['category']:<30}")
            print(f"    Description: {anomaly['description'][:50]}")
            print(f"    Amount: ${anomaly['amount']:,.2f}")
            print(f"    Reason: {anomaly['reason']}")
            print()
    else:
        print("\n  ✓ No anomalies detected. Transaction amounts are within expected ranges.\n")
    
    # === RECURRING CHARGES PATTERN ===
    print("  RECURRING CHARGES DETECTED")
    print("  " + "─" * 68)
    
    # Look for similar amounts on similar dates (simplified recurring detection)
    recurring_patterns = defaultdict(list)
    for cat, data in categories.items():
        for item in data["items"]:
            if item["amount"] < 0:
                amt = abs(item["amount"])
                # Group by amount (rounded to nearest dollar)
                amt_key = round(amt)
                recurring_patterns[amt_key].append({
                    "category": cat,
                    "date": item["date"],
                    "desc": item["desc"]
                })
    
    recurring_found = False
    for amt, entries in sorted(recurring_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        if len(entries) >= 2:
            recurring_found = True
            print(f"\n  ${amt:,.2f} appears {len(entries)} time(s):")
            for entry in entries:
                print(f"    {entry['date']} | {entry['category']} | {entry['desc'][:40]}")
    
    if not recurring_found:
        print("\n  No recurring charge patterns detected in this month.")
    
    print()
    print("=" * 72)
    
    # === MONTH COMPARISON (if previous month has data) ===
    print()
    print("  MONTH-OVER-MONTH COMPARISON")
    print("  " + "─" * 68)
    
    # Get previous month
    if now.month == 1:
        prev_month_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
        prev_month_end = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        prev_month_label = "December " + str(now.year - 1)
    else:
        prev_month_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
        prev_month_end = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        prev_month_label = datetime(now.year, now.month - 1, 1).strftime("%B %Y")
    
    # Calculate previous month metrics from the same data
    prev_income = 0.0
    prev_expense = 0.0
    prev_categories = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0, "items": []})
    prev_category_transactions = defaultdict(list)
    
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        
        date_raw = tx.get('postedAt') or tx.get('date')
        if not date_raw:
            continue
        
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except:
            continue
        
        if tx_date < prev_month_start or tx_date >= prev_month_end:
            continue
        
        desc = tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amount = float(tx.get('amount', 0))
        
        special_category, special_type = classify_special(desc)
        
        if special_type == "exclude":
            continue
        
        if special_type == "capital":
            prev_categories[special_category]["income"] += amount
            prev_categories[special_category]["count"] += 1
            item = {"date": tx_date.strftime('%Y-%m-%d'), "desc": desc[:50], "amount": amount}
            prev_categories[special_category]["items"].append(item)
            prev_category_transactions[special_category].append(item)
            prev_income += amount
            continue
        
        category = categorizer.categorize(desc)
        
        if amount > 0:
            prev_categories[category]["income"] += amount
        else:
            prev_categories[category]["expense"] += abs(amount)
        
        prev_categories[category]["count"] += 1
        item = {"date": tx_date.strftime('%Y-%m-%d'), "desc": desc[:50], "amount": amount}
        prev_categories[category]["items"].append(item)
        prev_category_transactions[category].append(item)
        
        if amount > 0:
            prev_income += amount
        else:
            prev_expense += abs(amount)
    
    prev_net = prev_income - prev_expense
    
    print(f"\n  {prev_month_label:<20} {month_label}")
    print(f"  {'─' * 20} {'─' * 20}")
    print(f"  {'Income:':<20} ${prev_income:>9,.2f}   ${total_income:>9,.2f}")
    print(f"  {'Expenses:':<20} ${prev_expense:>9,.2f}   ${total_expense:>9,.2f}")
    print(f"  {'Net:':<20} ${prev_net:>9,.2f}   ${net_profit:>9,.2f}")
    print(f"  {'Margin:':<20} {(prev_net/prev_income*100 if prev_income > 0 else 0):>8.1f}%   {(net_profit/total_income*100 if total_income > 0 else 0):>8.1f}%")
    print(f"  {'Transactions:':<20} {len([t for t in month_transactions if t]):>10,}   {total_items:>10,}")
    
    # Month-over-month changes
    if prev_income > 0 and total_income > 0:
        income_change = ((total_income - prev_income) / prev_income) * 100
        print(f"\n  Income change:     {income_change:+.1f}%")
    
    if prev_expense > 0 and total_expense > 0:
        expense_change = ((total_expense - prev_expense) / prev_expense) * 100
        print(f"  Expense change:    {expense_change:+.1f}%")
    
    print()
    print("=" * 72)
    
    # === KEY TAKEAWAYS ===
    print()
    print("  KEY TAKEAWAYS")
    print("  " + "─" * 68)
    
    if net_profit >= 0:
        print(f"\n  ✓ The company is profitable this month with a net income of ${net_profit:,.2f}.")
    else:
        print(f"\n  ⚠ The company operated at a loss this month (${net_profit:,.2f}).")
    
    if total_expense > 0:
        largest_expense_cat = max(categories.items(), key=lambda x: x[1]["expense"])
        if largest_expense_cat[1]["expense"] > 0:
            print(f"  Largest expense category: {largest_expense_cat[0]} (${largest_expense_cat[1]['expense']:,.2f})")
    
    if total_income > 0:
        largest_income_cat = max(categories.items(), key=lambda x: x[1]["income"])
        if largest_income_cat[1]["income"] > 0:
            print(f"  Primary revenue source: {largest_income_cat[0]} (${largest_income_cat[1]['income']:,.2f})")
    
    if anomalies:
        print(f"  ⚠ {len(anomalies)} anomaly/ anomalies detected — see Anomaly Detection section above.")
    
    print()
    print("=" * 72)


if __name__ == "__main__":
    generate_monthly_report()
