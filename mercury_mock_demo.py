import os
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class Transaction:
    date: datetime
    description: str
    amount: Decimal
    currency: str
    category: str = "Miscellaneous"

def categorize_transaction(description: str) -> str:
    """
    Assigns a category to a transaction based on keywords in its description.
    """
    desc_lower = description.lower()
    
    if any(k in desc_lower for k in ["aws", "google cloud", "digitalocean", "azure"]):
        return "Infrastructure"
    elif any(k in desc_lower for k in ["starbucks", "cafe", "restaurant", "eatery", "food"]):
        return "Meals & Entertainment"
    elif any(k in desc_lower for k in ["uber", "lyft", "airline", "flight", "taxi"]):
        return "Travel"
    elif any(k in desc_lower for k in ["stripe", "paypal", "client payment", "deposit", "revenue"]):
        return "Revenue"
    else:
        return "Miscellaneous"

def run_mock_demo():
    # 1. Define Mock Data
    mock_raw_data = [
        {"date": "2026-07-01", "description": "AWS Cloud Services", "amount": -150.00, "currency": "USD"},
        {"date": "2026-07-02", "description": "Stripe Payout", "amount": 2500.00, "currency": "USD"},
        {"date": "2026-07-03", "description": "Starbucks Coffee", "amount": -6.50, "currency": "USD"},
        {"date": "2026-07-03", "description": "Google Cloud Platform", "amount": -45.00, "currency": "USD"},
        {"date": "2026-07-04", "description": "Uber Trip", "amount": -22.00, "currency": "USD"},
        {"date": "2026-07-04", "description": "Local Cafe", "amount": -8.00, "currency": "USD"},
        {"date": "2026-07-05", "description": "Client Payment: Project X", "amount": 1200.00, "currency": "USD"},
    ]

    # 2. Process Data into Transaction objects
    transactions = []
    for item in mock_raw_data:
        try:
            transactions.append(Transaction(
                date=datetime.strptime(item["date"], "%Y-%m-%d"),
                description=item["description"],
                amount=Decimal(str(item["amount"])),
                currency=item["currency"],
                category=categorize_transaction(item["description"])
            ))
        except Exception as e:
            print(f"Error processing transaction {item}: {e}")

    # 3. Calculate Summary
    total_revenue = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = sum(t.amount for t in transactions if t.amount < 0)
    net_cash_flow = total_revenue + total_expenses

    # 4. Print Report
    print("=" * 80)
    print(f"{'MERCURY TRANSACTION REPORT (MOCK DEMO)':^80}")
    print("=" * 80)
    print(f"{'Date':<12} | {'Description':<25} | {'Category':<18} | {'Amount':<10} | {'Curr'}")
    print("-" * 80)

    for t in transactions:
        date_str = t.date.strftime("%Y-%m-%d")
        desc_str = (t.description[:24] + "...") if len(t.description) > 24 else t.description
        amount_str = f"{t.amount:>10.2f}"
        print(f"{date_str:<12} | {desc_str:<25} | {t.category:<18} | {amount_str} | {t.currency}")

    print("-" * 80)
    print(f"{'SUMMARY':<12} | {'':<25} | {'':<18} | {'':<10} |")
    print(f"{'':<12} | {'':<25} | {'':<18} | {'Total Revenue:':<10} | {total_revenue:>10.2f}")
    print(f"{'':<12} | {'':<25} | {'':<18} | {'Total Expense:':<10} | {total_expenses:>10.2f}")
    print(f"{'':<12} | {'':<25} | {'':<18} | {'Net Flow:':<10} | {net_cash_flow:>10.2f}")
    print("=" * 80)

if __name__ == "__main__":
    run_mock_demo()
