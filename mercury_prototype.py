import os
import requests
from dotenv import load_dotenv

def fetch_mercury_transactions():
    """
    Fetches and prints the transactions from the first account found in Mercury.
    """
    # 1. Load environment variables from the local .env file
    load_dotenv()

    # Get the API key from the environment
    api_key = os.getenv("mercury_production_api_key")

    # Verify that the API key was loaded successfully
    if not api_key:
        print("Error: 'mercury_production_api_key' not found in the .env file.")
        return

    # Set up headers for Bearer authentication
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # 2. Fetch all accounts
        accounts_url = "https://api.mercury.com/api/v1/accounts"
        accounts_response = requests.get(accounts_url, headers=headers, timeout=10)
        accounts_response.raise_for_status()
        
        accounts_data = accounts_response.json()
        
        # Mercury API typically returns data in a 'data' field
        accounts = accounts_data.get('data', []) if isinstance(accounts_data, dict) else accounts_data

        if not accounts:
            print("No accounts found.")
            return

        # 3. Pick the first account
        first_account = accounts[0]
        account_id = first_account.get('id')
        account_name = first_account.get('name', 'Unknown Account')

        if not account_id:
            print("Error: Could not retrieve account ID from the first account.")
            return

        print(f"Fetching transactions for account: {account_name} ({account_id})")

        # Fetch transactions for this specific account
        transactions_url = f"https://api.mercury.com/api/v1/account/{account_id}/transactions"
        transactions_response = requests.get(transactions_url, headers=headers, timeout=10)
        transactions_response.raise_for_status()

        transactions_data = transactions_response.json()
        transactions = transactions_data.get('data', []) if isinstance(transactions_data, dict) else transactions_data

        if not transactions:
            print("No transactions found for this account.")
            return

        # 4. Print the transaction details in a nice table
        print(f"\n{'Date':<12} | {'Description':<30} | {'Amount':<10} | {'Currency':<5}")
        print("-" * 65)

        for tx in transactions:
            # Use .get() to safely access dictionary keys and provide defaults
            date = tx.get('date', 'N/A')
            description = tx.get('description', 'N/A')
            amount = tx.get('amount', 0.0)
            currency = tx.get('currency', 'USD')

            # Truncate description if it's too long for the table view
            display_desc = (description[:27] + '...') if len(description) > 30 else description

            print(f"{str(date):<12} | {display_desc:<30} | {amount:<10} | {currency:<5}")

    except requests.exceptions.HTTPError as http_err:
        # Handle specific HTTP errors
        status_code = http_err.response.status_code
        if status_code == 401:
            print("Error: Invalid API key. Please check your .env file.")
        elif status_code == 403:
            print("Error: Permission denied. Check your API key permissions.")
        elif status_code == 404:
            print("Error: Resource not found.")
        else:
            print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the Mercury API. Check your internet connection.")
    except requests.exceptions.Timeout:
        print("Error: The request timed out.")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the request: {req_err}")
    except ValueError as json_err:
        print(f"Error parsing the API response: {json_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_mercury_transactions()
