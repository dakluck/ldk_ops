"""
Monthly Financial Report for LDK International LLC.
Fetches Mercury transactions for the specified month (defaults to preceding closed month on days 1-5, or current month)
and produces:
- Key financial metrics (Operating Revenue, Operating Expenses, Net Profit/Loss)
- Balance sheet capital contributions tracking (Owner Equity)
- Category breakdown prioritizing Mercury Books Chart of Accounts
- Anomaly detection (unusual amounts, statistical outliers via IQR, failed billing attempts)
- Month-over-month operating comparison
- Executive HTML email delivery to dailey@ldk-international.com
"""
import os
import sys
import argparse
from datetime import datetime, timezone
from collections import defaultdict
from statistics import median
from typing import Optional, Dict, Any, List

_reports_dir = os.path.dirname(os.path.abspath(__file__))
_agent_dir = os.path.dirname(_reports_dir)
_ldk_ops_dir = os.path.dirname(_agent_dir)
sys.path.insert(0, _ldk_ops_dir)
sys.path.insert(0, _agent_dir)
os.chdir(_agent_dir)

from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer
from email_sender import send_email

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


def detect_failed_transactions(month_failed_txns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Summarize failed transaction attempts in the month (e.g. billing retries or failed regulatory debits).
    Returns a list of structured alert objects.
    """
    if not month_failed_txns:
        return []
    
    payee_groups = defaultdict(list)
    for t in month_failed_txns:
        payee = t.get('desc', 'Unknown')
        payee_groups[payee].append(t)
    
    alerts = []
    for payee, txns in payee_groups.items():
        total_attempted = sum(abs(t['amount']) for t in txns)
        latest_date = max(t['date'] for t in txns)
        count = len(txns)
        clean_payee = payee.lower()
        
        is_tax_or_critical = any(kw in clean_payee for kw in ["tax", "franchise", "irs", "ftb", "payroll", "corporate"])
        
        if is_tax_or_critical:
            alerts.append({
                "severity": "CRITICAL",
                "payee": payee,
                "count": count,
                "amount": abs(txns[0]['amount']),
                "latest_date": latest_date,
                "reason": f"REGULATORY / TAX DEBIT FAILED: {payee} failed {count} time(s) (sample amount: ${abs(txns[0]['amount']):,.2f}) on {latest_date}. Action required: Verify state tax portal status."
            })
        else:
            alerts.append({
                "severity": "WARNING" if total_attempted > 100 else "INFO",
                "payee": payee,
                "count": count,
                "amount": abs(txns[0]['amount']),
                "latest_date": latest_date,
                "reason": f"Billing retry alert: {payee} had {count} failed billing attempt(s) (sample amount: ${abs(txns[0]['amount']):,.2f})."
            })
            
    return alerts


def build_html_email(
    month_label: str,
    operating_revenue: float,
    operating_expense: float,
    net_operating_profit: float,
    margin_pct: Optional[float],
    total_capital: float,
    net_cash_flow: float,
    operating_categories: dict,
    all_expenses: list,
    all_income: list,
    capital_items: list,
    anomalies: list,
    failed_alerts: list,
    mom_data: dict,
    gcp_summary: Optional[dict] = None
) -> str:
    """Builds a responsive, executive HTML email statement for LDK International LLC."""
    
    is_profit = net_operating_profit >= 0
    status_text = "Operating Profit" if is_profit else "Operating Loss"
    status_bg = "#f0fff4" if is_profit else "#fff5f5"
    status_color = "#276749" if is_profit else "#c53030"
    status_border = "#c6f6d5" if is_profit else "#fed7d7"

    # 1. Category table rows
    cat_rows_html = ""
    sorted_cats = sorted(operating_categories.items(), key=lambda x: abs(x[1]["income"] - x[1]["expense"]), reverse=True)
    for cat, data in sorted_cats:
        if data["count"] == 0:
            continue
        exp = data["expense"]
        inc = data["income"]
        exp_pct = (exp / operating_expense * 100) if operating_expense > 0 else 0.0
        
        cat_type = "Expense" if exp > 0 and inc == 0 else ("Revenue" if inc > 0 and exp == 0 else "Mixed")
        amt_str = f"-${exp:,.2f}" if exp > 0 else f"+${inc:,.2f}"
        
        cat_rows_html += f"""
        <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #edf2f7; font-weight: 500; font-size: 13px; color: #2d3748;">{cat}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #edf2f7; font-size: 13px; color: #718096;">{cat_type}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #edf2f7; text-align: center; font-size: 13px; color: #718096;">{data['count']}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #edf2f7; text-align: right; font-weight: 600; font-size: 13px; color: #2d3748;">{amt_str}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #edf2f7; text-align: right; font-size: 13px; color: #718096;">{exp_pct:.1f}%</td>
        </tr>
        """

    # 2. Itemized Top Expenses rows
    expense_rows_html = ""
    if all_expenses:
        for cat, item in all_expenses[:15]:
            expense_rows_html += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-size: 12px; color: #718096;">{item['date']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-size: 12px; font-weight: 500; color: #2d3748;">{item['desc']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-size: 12px; color: #718096;">{cat}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; font-size: 12px; font-weight: 600; color: #c53030;">${abs(item['amount']):,.2f}</td>
            </tr>
            """
    else:
        expense_rows_html = "<tr><td colspan='4' style='padding: 12px; text-align: center; color: #a0aec0; font-size: 13px;'>No operating expenses recorded in this period.</td></tr>"

    # 3. Capital Contributions rows
    capital_rows_html = ""
    if capital_items:
        for item in capital_items:
            capital_rows_html += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-size: 12px; color: #718096;">{item['date']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-size: 12px; font-weight: 500; color: #2d3748;">{item['desc']}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-size: 12px; color: #6b46c1;">Owner Equity / Deposit</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; font-size: 12px; font-weight: 600; color: #276749;">+${item['amount']:,.2f}</td>
            </tr>
            """

    # 4. Alerts and Anomalies box
    alerts_html = ""
    all_alerts = []
    for fa in failed_alerts:
        all_alerts.append((fa['severity'], fa['reason']))
    for an in anomalies:
        all_alerts.append(("ANOMALY", f"[{an['category']}] {an['description']}: {an['reason']} (${an['amount']:,.2f})"))
    
    if all_alerts:
        items_html = "".join([
            f"<li style='margin-bottom: 8px; font-size: 13px; line-height: 1.4; color: #2d3748;'>"
            f"<strong style='color: {'#c53030' if sev == 'CRITICAL' else ('#dd6b20' if sev == 'WARNING' else '#3182ce')};'>[{sev}]</strong> "
            f"{msg}</li>"
            for sev, msg in all_alerts
        ])
        alerts_html = f"""
        <div style="background-color: #fffaf0; border-left: 4px solid #dd6b20; border-radius: 6px; padding: 16px 20px; margin: 24px 0;">
            <h4 style="margin: 0 0 10px 0; color: #c05621; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">⚠️ Operational & Billing Alerts ({len(all_alerts)})</h4>
            <ul style="margin: 0; padding-left: 18px;">
                {items_html}
            </ul>
        </div>
        """

    # 5. Month-over-Month calculation
    diff_rev = operating_revenue - mom_data['prev_operating_rev']
    diff_exp = operating_expense - mom_data['prev_operating_exp']
    diff_net = net_operating_profit - mom_data['prev_net_operating']
    diff_cap = total_capital - mom_data['prev_capital']

    def format_diff(val: float, is_expense: bool = False):
        if val == 0:
            return "$0.00"
        sign = "+" if val > 0 else "-"
        # For expenses, increase is red, decrease is green
        if is_expense:
            color = "#c53030" if val > 0 else "#276749"
        else:
            color = "#276749" if val > 0 else "#c53030"
        return f"<span style='color: {color}; font-weight: 600;'>{sign}${abs(val):,.2f}</span>"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 660px; margin: 0 auto; color: #1a202c; line-height: 1.5; padding: 24px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;">
        
        <!-- Header -->
        <div style="border-bottom: 2px solid #2b6cb0; padding-bottom: 14px; margin-bottom: 22px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="vertical-align: top;">
                        <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #2b6cb0; font-weight: 700;">LDK International LLC &bull; Financial Intelligence</span>
                        <h2 style="margin: 4px 0 0 0; color: #2d3748; font-size: 22px;">Monthly Financial Statement (P&L)</h2>
                        <p style="margin: 4px 0 0 0; font-size: 13px; color: #718096;">Accounting Period: <strong>{month_label}</strong></p>
                    </td>
                    <td style="vertical-align: top; text-align: right;">
                        <span style="display: inline-block; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; text-transform: uppercase; background: {status_bg}; color: {status_color}; border: 1px solid {status_border};">
                            {status_text}
                        </span>
                    </td>
                </tr>
            </table>
        </div>

        <!-- 4 Key Metric Cards (2x2 table) -->
        <table style="width: 100%; border-collapse: separate; border-spacing: 12px; margin-bottom: 16px;">
            <tr>
                <td style="width: 50%; background: #ebf8ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 26px; font-weight: 700; color: #2b6cb0;">${operating_revenue:,.2f}</div>
                    <div style="font-size: 11px; color: #4a5568; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Operating Revenue</div>
                    <div style="font-size: 11px; color: #3182ce; margin-top: 4px;">Mercury Books / Merchant Inflow</div>
                </td>
                <td style="width: 50%; background: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 26px; font-weight: 700; color: #c53030;">${operating_expense:,.2f}</div>
                    <div style="font-size: 11px; color: #4a5568; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Operating Expenses</div>
                    <div style="font-size: 11px; color: #e53e3e; margin-top: 4px;">{len(all_expenses)} active business item(s)</div>
                </td>
            </tr>
            <tr>
                <td style="width: 50%; background: {status_bg}; border: 1px solid {status_border}; border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 26px; font-weight: 700; color: {status_color};">
                        {'-' if net_operating_profit < 0 else '+'}${abs(net_operating_profit):,.2f}
                    </div>
                    <div style="font-size: 11px; color: #4a5568; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Net Operating Income</div>
                    <div style="font-size: 11px; color: {status_color}; margin-top: 4px;">
                        {'Margin: ' + f'{margin_pct:.1f}%' if margin_pct is not None else 'Pre-Revenue Operations'}
                    </div>
                </td>
                <td style="width: 50%; background: #faf5ff; border: 1px solid #e9d8fd; border-radius: 8px; padding: 16px; text-align: center;">
                    <div style="font-size: 26px; font-weight: 700; color: #6b46c1;">+${total_capital:,.2f}</div>
                    <div style="font-size: 11px; color: #4a5568; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Owner Capital Injected</div>
                    <div style="font-size: 11px; color: #805ad5; margin-top: 4px;">Net Cash Flow: <strong>{'+' if net_cash_flow >= 0 else '-'}${abs(net_cash_flow):,.2f}</strong></div>
                </td>
            </tr>
        </table>

        <!-- Alerts -->
        {alerts_html}

        <!-- Month-over-Month Comparison -->
        <div style="margin-top: 24px; margin-bottom: 24px;">
            <h3 style="margin: 0 0 10px 0; color: #2d3748; font-size: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                📈 Month-over-Month Operating Comparison
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f7fafc; color: #718096; text-align: left;">
                        <th style="padding: 8px 12px; font-weight: 600;">Metric</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">{mom_data['prev_month_label']}</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">{month_label}</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">MoM Change</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-weight: 500;">Operating Revenue</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568;">${mom_data['prev_operating_rev']:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568; font-weight: 600;">${operating_revenue:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right;">{format_diff(diff_rev)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-weight: 500;">Operating Expenses</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568;">${mom_data['prev_operating_exp']:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568; font-weight: 600;">${operating_expense:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right;">{format_diff(diff_exp, is_expense=True)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-weight: 500;">Net Operating Income</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568;">${mom_data['prev_net_operating']:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568; font-weight: 600;">${net_operating_profit:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right;">{format_diff(diff_net)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-weight: 500;">Operating Margin</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #718096;">{mom_data['prev_margin_str']}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #718096; font-weight: 600;">{mom_data['curr_margin_str']}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #718096;">—</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; font-weight: 500;">Owner Capital Injections</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568;">${mom_data['prev_capital']:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right; color: #4a5568; font-weight: 600;">${total_capital:,.2f}</td>
                        <td style="padding: 8px 12px; border-bottom: 1px solid #edf2f7; text-align: right;">{format_diff(diff_cap)}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Expenses by Category -->
        <div style="margin-top: 24px; margin-bottom: 24px;">
            <h3 style="margin: 0 0 10px 0; color: #2d3748; font-size: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                📂 Operating Breakdown by Category (P&L)
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f7fafc; color: #718096; text-align: left;">
                        <th style="padding: 8px 12px; font-weight: 600;">Category</th>
                        <th style="padding: 8px 12px; font-weight: 600;">Type</th>
                        <th style="padding: 8px 12px; text-align: center; font-weight: 600;">Count</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">Net Amount</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">Share</th>
                    </tr>
                </thead>
                <tbody>
                    {cat_rows_html}
                </tbody>
            </table>
        </div>

        <!-- Itemized Expenses -->
        <div style="margin-top: 24px; margin-bottom: 24px;">
            <h3 style="margin: 0 0 10px 0; color: #2d3748; font-size: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                💳 Itemized Operating Expenses
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background-color: #f7fafc; color: #718096; text-align: left;">
                        <th style="padding: 8px 12px; font-weight: 600;">Date</th>
                        <th style="padding: 8px 12px; font-weight: 600;">Description</th>
                        <th style="padding: 8px 12px; font-weight: 600;">Category</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {expense_rows_html}
                </tbody>
            </table>
        </div>

        <!-- Owner Capital Contributions -->
        {f'''
        <div style="margin-top: 24px; margin-bottom: 24px;">
            <h3 style="margin: 0 0 10px 0; color: #2d3748; font-size: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
                🏦 Owner Capital & Equity Deposits
            </h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background-color: #f7fafc; color: #718096; text-align: left;">
                        <th style="padding: 8px 12px; font-weight: 600;">Date</th>
                        <th style="padding: 8px 12px; font-weight: 600;">Description</th>
                        <th style="padding: 8px 12px; font-weight: 600;">Account / Class</th>
                        <th style="padding: 8px 12px; text-align: right; font-weight: 600;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {capital_rows_html}
                </tbody>
            </table>
        </div>
        ''' if capital_items else ''}

        <!-- Footer -->
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 28px 0 16px 0;">
        <p style="font-size: 11px; color: #a0aec0; text-align: center; margin: 0;">
            Dispatched autonomously by <strong>Leo (LDK Ops)</strong> &bull; Mercury API Integration &bull; Scheduled Monthly P&L
        </p>
    </div>
    """
    return html_content


def generate_monthly_report(
    target_month: Optional[str] = None,
    send_email_report: bool = True,
    email_recipient: str = "dailey@ldk-international.com",
    force_current: bool = False,
    force_previous: bool = False,
    from_account: str = "leo"
):
    """Generate a comprehensive monthly financial report aligned with Mercury Books and dispatch via email."""
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    
    transactions = client.get_transactions()
    print(f"Total transactions fetched from Mercury: {len(transactions)}")
    print()
    
    now = datetime.now(timezone.utc)
    
    # Determine the target month to analyze
    if target_month:
        try:
            parts = target_month.strip().split("-")
            target_year = int(parts[0])
            target_month_num = int(parts[1])
            target_start = datetime(target_year, target_month_num, 1, tzinfo=timezone.utc)
        except Exception as e:
            print(f"Invalid target month '{target_month}'. Use YYYY-MM format. Defaulting.")
            target_start = None
    else:
        target_start = None
        
    if target_start is None:
        if force_previous:
            if now.month == 1:
                target_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
            else:
                target_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
        elif force_current:
            target_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        else:
            # Default behavior:
            # On the 1st through 5th of each month (e.g. when the monthly cron triggers),
            # report on the previous full calendar month that just closed.
            if now.day <= 5:
                if now.month == 1:
                    target_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
                else:
                    target_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
            else:
                target_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    if target_start.month == 12:
        target_end = datetime(target_start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        target_end = datetime(target_start.year, target_start.month + 1, 1, tzinfo=timezone.utc)
        
    month_label = target_start.strftime("%B %Y")
    
    # Calculate previous month for month-over-month comparison
    if target_start.month == 1:
        prev_month_start = datetime(target_start.year - 1, 12, 1, tzinfo=timezone.utc)
        prev_month_end = datetime(target_start.year, 1, 1, tzinfo=timezone.utc)
        prev_month_label = f"December {target_start.year - 1}"
    else:
        prev_month_start = datetime(target_start.year, target_start.month - 1, 1, tzinfo=timezone.utc)
        prev_month_end = datetime(target_start.year, target_start.month, 1, tzinfo=timezone.utc)
        prev_month_label = prev_month_start.strftime("%B %Y")
    
    print("=" * 72)
    print(f"  LDK INTERNATIONAL — MONTHLY FINANCIAL REPORT")
    print(f"  Period: {month_label}")
    print("=" * 72)
    print()
    
    # Filter for target month
    month_transactions = []
    month_failed_txns = []
    failed_retries_count = 0
    
    for tx in transactions:
        if not isinstance(tx, dict):
            continue

        date_raw = tx.get('postedAt') or tx.get('createdAt') or tx.get('date')
        if not date_raw:
            continue
        
        try:
            tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
        except Exception:
            continue
        
        if tx_date < target_start or tx_date >= target_end:
            continue
        
        if tx.get('status') == 'failed':
            failed_retries_count += 1
            month_failed_txns.append({
                "date": tx_date.strftime('%Y-%m-%d'),
                "desc": tx.get('counterpartyName') or tx.get('bankDescription') or tx.get('description') or 'Unknown',
                "amount": float(tx.get('amount', 0))
            })
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
        tx_date = datetime.fromisoformat(date_raw.replace('Z', '+00:00')) if date_raw else target_start
        
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
    margin_pct = (net_operating_profit / operating_revenue * 100) if operating_revenue > 0 else None
    
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
    
    if margin_pct is not None:
        print(f"  Operating Profit Margin: {margin_pct:>9.1f}%")
    
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
    all_income = []
    for cat, data in operating_categories.items():
        for item in data["items"]:
            if item["amount"] > 0:
                all_income.append((cat, item))
    all_income.sort(key=lambda x: x[1]["amount"], reverse=True)
    
    if operating_revenue > 0:
        print("  OPERATING REVENUE ITEMS")
        print("  " + "─" * 68)
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
    gcp_summary = None
    try:
        from gcp_billing import get_gcp_billing_summary
        gcp_summary = get_gcp_billing_summary(target_start)
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
    print("  ANOMALY DETECTION & BILLING ALERTS")
    print("  " + "─" * 68)
    anomalies = detect_anomalies(category_transactions)
    failed_alerts = detect_failed_transactions(month_failed_txns)
    
    if anomalies or failed_alerts:
        print(f"\n  ⚠️  Found {len(anomalies) + len(failed_alerts)} item(s) of interest:\n")
        for alert in failed_alerts:
            print(f"  [{alert['severity']}] {alert['latest_date']} | Payee: {alert['payee']}")
            print(f"    Reason: {alert['reason']}")
            print()
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
    
    prev_margin_str = f"{(prev_net_operating/prev_operating_rev*100):>9.1f}%" if prev_operating_rev > 0 else "      N/A"
    curr_margin_str = f"{(net_operating_profit/operating_revenue*100):>9.1f}%" if operating_revenue > 0 else "      N/A"
    
    print(f"\n  {'Metric':<25} {prev_month_label:<18} {month_label:<18}")
    print(f"  {'─' * 25} {'─' * 18} {'─' * 18}")
    print(f"  {'Operating Revenue:':<25} ${prev_operating_rev:>10,.2f}        ${operating_revenue:>10,.2f}")
    print(f"  {'Operating Expenses:':<25} ${prev_operating_exp:>10,.2f}        ${operating_expense:>10,.2f}")
    print(f"  {'Net Operating Income:':<25} ${prev_net_operating:>10,.2f}        ${net_operating_profit:>10,.2f}")
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
    
    if anomalies or failed_alerts:
        print(f"  ⚠ {len(anomalies) + len(failed_alerts)} item(s) flagged for operational review.")
    
    print("=" * 72)
    
    mom_data = {
        "prev_month_label": prev_month_label,
        "prev_operating_rev": prev_operating_rev,
        "prev_operating_exp": prev_operating_exp,
        "prev_net_operating": prev_net_operating,
        "prev_margin_str": prev_margin_str.strip(),
        "curr_margin_str": curr_margin_str.strip(),
        "prev_capital": prev_capital,
        "prev_items_count": prev_items_count
    }
    
    # === EMAIL DISPATCH ===
    if send_email_report:
        print(f"\n📧 Preparing Monthly Financial Report email for {email_recipient}...")
        html_body = build_html_email(
            month_label=month_label,
            operating_revenue=operating_revenue,
            operating_expense=operating_expense,
            net_operating_profit=net_operating_profit,
            margin_pct=margin_pct,
            total_capital=total_capital,
            net_cash_flow=net_cash_flow,
            operating_categories=operating_categories,
            all_expenses=all_expenses,
            all_income=all_income,
            capital_items=capital_items,
            anomalies=anomalies,
            failed_alerts=failed_alerts,
            mom_data=mom_data,
            gcp_summary=gcp_summary
        )
        
        status_tag = f"+${net_operating_profit:,.2f}" if net_operating_profit >= 0 else f"-${abs(net_operating_profit):,.2f}"
        subject = f"📊 LDK International Monthly Financial Statement — {month_label} [Net: {status_tag} | Cash Flow: {'+' if net_cash_flow >= 0 else '-'}${abs(net_cash_flow):,.2f}]"
        
        recipients = [r.strip() for r in email_recipient.split(",") if r.strip()]
        success = send_email(
            subject=subject,
            body=html_body,
            recipients=recipients,
            from_account=from_account,
            is_html=True
        )
        if success:
            print(f"🎉 Monthly financial statement successfully dispatched to: {', '.join(recipients)}")
        else:
            print(f"❌ Failed to dispatch email to: {', '.join(recipients)}", file=sys.stderr)
        return success
    else:
        print("\nℹ️  Email dispatch skipped (--dry-run / --no-email specified).")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LDK International Monthly Financial Report & P&L Statement")
    parser.add_argument("--month", help="Target month in YYYY-MM format (e.g. 2026-09). Defaults to previous completed month on days 1-5, or current month.")
    parser.add_argument("--previous", "--prev", action="store_true", help="Force report for previous completed month")
    parser.add_argument("--current", action="store_true", help="Force report for current calendar month")
    parser.add_argument("--email", default="dailey@ldk-international.com", help="Recipient email address (default: dailey@ldk-international.com)")
    parser.add_argument("--dry-run", "--no-email", action="store_true", help="Print report to console without sending email")
    parser.add_argument("--from-account", choices=["leo", "dailey_ldk", "dailey_personal"], default="leo", help="Sender email account (default: leo)")
    
    args = parser.parse_args()
    
    generate_monthly_report(
        target_month=args.month,
        send_email_report=not args.dry_run,
        email_recipient=args.email,
        force_current=args.current,
        force_previous=args.previous,
        from_account=args.from_account
    )
