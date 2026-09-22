"""
Monthly Financial Report for LDK International LLC.
Fetches Mercury transactions for the current month and produces:
- Key financial metrics (Operating Revenue, Operating Expenses, Net Profit/Loss)
- Balance sheet capital contributions tracking (Owner Equity)
- Category breakdown prioritizing Mercury Books Chart of Accounts
- Anomaly detection (unusual amounts, statistical outliers via IQR)
- Month-over-month operating comparison
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

# Internal transfers or circular payments to exclude
TRANSFER_PATTERNS_EXCLUDE = [
    "io autopay", "io payment", "mercury io cashback",
]

# Patterns representing owner equity / capital contributions
FOUNDER_FUNDING_PATTERNS = [
    "transfer from another bank",
    "elevations credit union",
    "account verification",
    "capital contribution",
    "founder funding",
]


def classify_special(desc: str, note: str = None):
    """
    Classify special non-operating transactions (internal transfers, founder funding).
    Returns (classification_name, type) where type is 'exclude', 'capital', or None.
    """
    clean_desc = (desc or "").lower().replace("*", " ").replace(";", " ").replace("  ", " ").strip()
    clean_note = (note or "").lower().strip()
    
    if any(p in clean_desc for p in TRANSFER_PATTERNS_EXCLUDE):
        return None, "exclude"
    
    if any(p in clean_desc for p in FOUNDER_FUNDING_PATTERNS) or "founder contribution" in clean_note:
        return "Owner Capital Contribution", "capital"
    
    return None, None


def detect_anomalies(category_transactions):
    """
    Detect anomalies in transaction amounts within a category.
    Uses IQR method: anything > Q3 + 1.5*IQR or < Q1 - 1.5*IQR is anomalous.
    Also flags single transactions that exceed $5,000.
    """
    anomalies = []
    
    for cat, txns in category_transactions.items():
        if len(txns) < 2:
            for t in txns:
                if abs(t['amount']) > 5000:
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
            if amt > upper_bound and iqr > 0:
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
    """Generate a comprehensive monthly financial report aligned with Mercury Books."""
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    transactions = client.get_transactions()
    print(f"Total transactions fetched from Mercury: {len(transactions)}")
    print()
    
    now = datetime.now(timezone.utc)
    current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        current_month_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        current_month_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    
    month_label = now.strftime("%B %Y")
    
    print("=" * 72)
    print(f"  LDK INTERNATIONAL — MONTHLY FINANCIAL REPORT")
    print(f"  Period: {month_label}")
    print("=" * 72)
    print()
    
    # Filter for current month, strictly ignoring failed transactions
    month_transactions = []
    failed_retries_count = 0
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        
        if tx.get('status') == 'failed':
            failed_retries_count += 1
            continue

        date_raw = tx.get('postedAt') or tx.get('createdAt') or tx.get('date')
        if not date_raw:
            continue
        
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except Exception:
            continue
        
        if tx_date < current_month_start or tx_date >= current_month_end:
            continue
        
        month_transactions.append(tx)
    
    print(f"Active Transactions in {month_label}: {len(month_transactions)} (Filtered out {failed_retries_count} failed billing retries)")
    print()
    
    operating_categories = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0, "items": []})
    capital_items = []
    total_capital = 0.0
    filtered_out = 0
    total_items = 0
    
    category_transactions = defaultdict(list)
    
    for tx in month_transactions:
        desc = tx.get('counterpartyName') or tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amount = float(tx.get('amount', 0))
        date_raw = tx.get('postedAt') or tx.get('createdAt') or tx.get('date')
        tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00')) if date_raw else now
        
        is_pending = tx.get('status') == 'pending'
        status_tag = " [PENDING]" if is_pending else ""
        
        special_category, special_type = classify_special(desc, note=tx.get('note'))
        
        if special_type == "exclude":
            filtered_out += 1
            continue
        
        if special_type == "capital":
            total_capital += amount
            item = {
                "date": tx_date.strftime('%Y-%m-%d'),
                "desc": f"{desc[:45]}{status_tag}",
                "amount": amount
            }
            capital_items.append(item)
            total_items += 1
            continue
        
        # Prioritize Mercury Books categoryData, fallback to local categorizer
        category_data = tx.get('categoryData')
        if category_data and category_data.get('name'):
            category = category_data.get('name')
        else:
            category = categorizer.categorize(desc)
        
        if amount > 0:
            operating_categories[category]["income"] += amount
        else:
            operating_categories[category]["expense"] += abs(amount)
        
        operating_categories[category]["count"] += 1
        item = {
            "date": tx_date.strftime('%Y-%m-%d'),
            "desc": f"{desc[:45]}{status_tag}",
            "amount": amount
        }
        operating_categories[category]["items"].append(item)
        category_transactions[category].append(item)
        total_items += 1
    
    operating_revenue = sum(d["income"] for d in operating_categories.values())
    operating_expense = sum(d["expense"] for d in operating_categories.values())
    net_operating_profit = operating_revenue - operating_expense
    net_cash_flow = net_operating_profit + total_capital
    
    # === PRINT CATEGORY BREAKDOWN ===
    print("  OPERATING REVENUE & EXPENSES BY CATEGORY (P&L)")
    print("  " + "─" * 68)
    
    sorted_cats = sorted(operating_categories.items(), key=lambda x: abs(x[1]["income"] - x[1]["expense"]), reverse=True)
    
    for cat, data in sorted_cats:
        if data["count"] == 0:
            continue
        
        net = data["income"] - data["expense"]
        if data["income"] > 0 and data["expense"] == 0:
            print(f"\n  {cat}")
            print(f"    Revenue:    ${data['income']:>10,.2f}  ({data['count']} transactions)")
        elif data["expense"] > 0 and data["income"] == 0:
            print(f"\n  {cat}")
            print(f"    Expenses:   ${data['expense']:>10,.2f}  ({data['count']} transactions)")
        else:
            print(f"\n  {cat}")
            print(f"    Revenue:    ${data['income']:>10,.2f}")
            print(f"    Expenses:   ${data['expense']:>10,.2f}")
            print(f"    Net:        ${net:>10,.2f}")
    
    print()
    print("  " + "─" * 68)
    print(f"\n  FINANCIAL SUMMARY")
    print(f"  " + "─" * 68)
    print(f"  Operating Revenue:       ${operating_revenue:>10,.2f}")
    print(f"  Operating Expenses:      ${operating_expense:>10,.2f}")
    print(f"  Net Operating Income:    ${net_operating_profit:>10,.2f}")
    if net_operating_profit >= 0:
        print(f"  Operating Status:        PROFIT")
    else:
        print(f"  Operating Status:        LOSS")
    
    if operating_revenue > 0:
        margin = (net_operating_profit / operating_revenue) * 100
        print(f"  Operating Profit Margin: {margin:>9.1f}%")
    
    print()
    print(f"  Owner Capital Additions: ${total_capital:>10,.2f} (Balance Sheet Equity)")
    print(f"  Net Cash Flow:           ${net_cash_flow:>10,.2f}")
    print(f"  Active Items Processed:  {total_items:>10} (Excluded {filtered_out} internal transfers)")
    print()
    
    # === TOP EXPENSES ===
    print("  TOP EXPENSES")
    print("  " + "─" * 68)
    
    all_expenses = []
    for cat, data in operating_categories.items():
        for item in data["items"]:
            if item["amount"] < 0:
                all_expenses.append((cat, item))
    
    all_expenses.sort(key=lambda x: abs(x[1]["amount"]), reverse=True)
    
    if all_expenses:
        for cat, item in all_expenses[:20]:
            print(f"  {item['date']} | {cat:<28} | {item['desc']:<25} | ${abs(item['amount']):>10,.2f}")
    else:
        print("  No operating expenses recorded in this period.")
    print()
    
    # === OPERATING REVENUE ITEMS ===
    if operating_revenue > 0:
        print("  OPERATING REVENUE ITEMS")
        print("  " + "─" * 68)
        all_income = []
        for cat, data in operating_categories.items():
            for item in data["items"]:
                if item["amount"] > 0:
                    all_income.append((cat, item))
        all_income.sort(key=lambda x: x[1]["amount"], reverse=True)
        for cat, item in all_income:
            print(f"  {item['date']} | {cat:<28} | {item['desc']:<25} | ${item['amount']:>10,.2f}")
        print()
    
    # === OWNER CAPITAL CONTRIBUTIONS ===
    if capital_items:
        print("  OWNER CAPITAL CONTRIBUTIONS (EQUITY)")
        print("  " + "─" * 68)
        for item in capital_items:
            print(f"  {item['date']} | {'Owner Capital / Equity':<28} | {item['desc']:<25} | ${item['amount']:>10,.2f}")
        print()

    # === GCP CLOUD INFRASTRUCTURE ATTRIBUTION (BIGQUERY EXPORT) ===
    try:
        from gcp_billing import get_gcp_billing_summary
        gcp_summary = get_gcp_billing_summary(now)
        if gcp_summary.get("status") == "success" and gcp_summary.get("total_net_cost", 0) > 0:
            print("  GCP CLOUD INFRASTRUCTURE ATTRIBUTION (BigQuery Export)")
            print("  " + "─" * 68)
            print(f"  Total Correlated GCP Spend: ${gcp_summary['total_net_cost']:,.2f}")
            print("\n  Spend by Project:")
            for proj, cost in gcp_summary.get("by_project", {}).items():
                pct = (cost / gcp_summary['total_net_cost']) * 100 if gcp_summary['total_net_cost'] > 0 else 0
                print(f"    • {proj:<28} ${cost:>8,.2f} ({pct:>5.1f}%)")
            print("\n  Top Cloud Services:")
            for srv, cost in list(gcp_summary.get("by_service", {}).items())[:5]:
                pct = (cost / gcp_summary['total_net_cost']) * 100 if gcp_summary['total_net_cost'] > 0 else 0
                print(f"    • {srv:<28} ${cost:>8,.2f} ({pct:>5.1f}%)")
            print()
    except Exception:
        pass

    # === ANOMALY DETECTION ===
    print("  ANOMALY DETECTION")
    print("  " + "─" * 68)
    anomalies = detect_anomalies(category_transactions)
    if anomalies:
        print(f"\n  ⚠️  Found {len(anomalies)} potential anomalies:\n")
        for anomaly in anomalies:
            print(f"  [{anomaly['type'].upper()}] {anomaly['date']} | {anomaly['category']:<28}")
            print(f"    Description: {anomaly['description']}")
            print(f"    Amount: ${anomaly['amount']:,.2f}")
            print(f"    Reason: {anomaly['reason']}")
            print()
    else:
        print("\n  ✓ No anomalies detected. Transaction amounts are within expected ranges.\n")
    
    # === MONTH-OVER-MONTH COMPARISON ===
    print("=" * 72)
    print("  MONTH-OVER-MONTH OPERATING COMPARISON")
    print("  " + "─" * 68)
    
    if now.month == 1:
        prev_month_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
        prev_month_end = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        prev_month_label = "December " + str(now.year - 1)
    else:
        prev_month_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
        prev_month_end = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        prev_month_label = datetime(now.year, now.month - 1, 1).strftime("%B %Y")
    
    prev_operating_rev = 0.0
    prev_operating_exp = 0.0
    prev_capital = 0.0
    prev_items_count = 0
    
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        if tx.get('status') == 'failed':
            continue
        
        date_raw = tx.get('postedAt') or tx.get('createdAt') or tx.get('date')
        if not date_raw:
            continue
        
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except Exception:
            continue
        
        if tx_date < prev_month_start or tx_date >= prev_month_end:
            continue
        
        desc = tx.get('counterpartyName') or tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amount = float(tx.get('amount', 0))
        
        special_category, special_type = classify_special(desc, note=tx.get('note'))
        if special_type == "exclude":
            continue
        if special_type == "capital":
            prev_capital += amount
            prev_items_count += 1
            continue
        
        if amount > 0:
            prev_operating_rev += amount
        else:
            prev_operating_exp += abs(amount)
        prev_items_count += 1
    
    prev_net_operating = prev_operating_rev - prev_operating_exp
    
    print(f"\n  {'Metric':<25} {prev_month_label:<18} {month_label:<18}")
    print(f"  {'─' * 25} {'─' * 18} {'─' * 18}")
    print(f"  {'Operating Revenue:':<25} ${prev_operating_rev:>10,.2f}        ${operating_revenue:>10,.2f}")
    print(f"  {'Operating Expenses:':<25} ${prev_operating_exp:>10,.2f}        ${operating_expense:>10,.2f}")
    print(f"  {'Net Operating Income:':<25} ${prev_net_operating:>10,.2f}        ${net_operating_profit:>10,.2f}")
    
    prev_margin_str = f"{(prev_net_operating/prev_operating_rev*100):>9.1f}%" if prev_operating_rev > 0 else "      N/A"
    curr_margin_str = f"{(net_operating_profit/operating_revenue*100):>9.1f}%" if operating_revenue > 0 else "      N/A"
    print(f"  {'Operating Margin:':<25} {prev_margin_str:<18} {curr_margin_str:<18}")
    print(f"  {'Owner Capital Adds:':<25} ${prev_capital:>10,.2f}        ${total_capital:>10,.2f}")
    print(f"  {'Total Transactions:':<25} {prev_items_count:>10}        {total_items:>10}")
    
    print()
    print("=" * 72)
    print("  KEY TAKEAWAYS")
    print("  " + "─" * 68)
    
    if net_operating_profit >= 0:
        print(f"\n  ✓ Company achieved operating profitability this month (${net_operating_profit:,.2f}).")
    else:
        print(f"\n  ⚠ Operating loss this month of -${abs(net_operating_profit):,.2f}.")
    
    if total_capital > 0:
        print(f"  ✓ Owner injected ${total_capital:,.2f} in capital contributions to fund operations.")
    
    if operating_expense > 0:
        largest_expense_cat = max(operating_categories.items(), key=lambda x: x[1]["expense"])
        if largest_expense_cat[1]["expense"] > 0:
            print(f"  Largest expense category: {largest_expense_cat[0]} (${largest_expense_cat[1]['expense']:,.2f})")
    
    if operating_revenue > 0:
        largest_income_cat = max(operating_categories.items(), key=lambda x: x[1]["income"])
        if largest_income_cat[1]["income"] > 0:
            print(f"  Primary revenue source: {largest_income_cat[0]} (${largest_income_cat[1]['income']:,.2f})")
    
    if anomalies:
        print(f"  ⚠ {len(anomalies)} anomaly alert(s) detected.")
    
    print("=" * 72)


if __name__ == "__main__":
    generate_monthly_report()
