
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

# Import manually if needed, but setting PYTHONPATH is cleaner
from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer

def analyze_gcp_trend():
    client = MercuryClient()
    categorizer = TransactionCategorizer()
    transactions = client.get_transactions()
    
    gcp_txs = []
    for tx in transactions:
        desc = tx.get('bankDescription') or tx.get('description') or ''
        if 'google cloud' in desc.lower():
            gcp_txs.append(tx)
            
    print(f"Found {len(gcp_txs)} Google Cloud transactions.")
    for tx in sorted(gcp_txs, key=lambda x: x.get('postedAt', '')):
        date = tx.get('postedAt') or tx.get('date') or 'N/A'
        desc = tx.get('bankDescription') or tx.get('description') or 'Unknown'
        amt = tx.get('amount', 0)
        print(f"{date} | {desc[:40]:<40} | ${amt:>10,.2f}")

if __name__ == '__main__':
    analyze_gcp_trend()
