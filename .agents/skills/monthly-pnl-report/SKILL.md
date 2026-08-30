---
name: monthly-pnl-report
description: >-
  Generates the monthly Profit & Loss (P&L) financial report from Mercury bank data,
  categorizes transactions, and prepares summary reports for LDK International.
  Use when the user asks for financial summaries, monthly P&L, or tax reporting.
---

# Monthly P&L Report Workflow

This skill executes monthly financial analysis and reporting for LDK International using the Mercury API integration.

## Key Files
- Script: [`monthly_report.py`](file:///home/dailey/Development/ldk_ops/finance_agent/reports/monthly_report.py)
- API Client: [`mercury_client.py`](file:///home/dailey/Development/ldk_ops/finance_agent/api/mercury_client.py)
- Categorizer: [`categorizer.py`](file:///home/dailey/Development/ldk_ops/finance_agent/core/categorizer.py)

---

## Execution Procedures

### 1. Run Monthly P&L Analysis
```bash
python3 /home/dailey/Development/ldk_ops/finance_agent/reports/monthly_report.py
```

### 2. Verification
Verify that the output contains:
- Total Inflows & Outflows
- Categorized Expenses (Cloud, SaaS, Contractors, Operations)
- Net Income summary
