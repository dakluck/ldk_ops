
from typing import List, Dict, Any

class TransactionCategorizer:
    def __init__(self, llm_client=None):
        """
        Initializes the categorizer.
        
        :param llm_client: An optional LLM client that implements a `complete(prompt: str) -> str` method.
        """
        self.llm_client = llm_client
        self.prompt_template = (
            "You are a financial assistant for LDK International LLC. Categorize the following transaction description "
            "into one of these official Mercury categories: [Software & Subscriptions, Revenue, Marketing & Advertising, "
            "Legal & Professional Services, Business Meals, Travel & Transportation, Office Supplies & Equipment, "
            "Bank Fees, Payment Processing Fees, Transfer].\n\n"
            "Transaction: {description}\n\n"
            "Category:"
        )

    def _build_prompt(self, description: str) -> str:
        return self.prompt_template.format(description=description)

    def _rule_based_categorize(self, description: str) -> str:
        """
        Rule-based categorization fallback when LLM client is not configured.
        """
        p = description.lower()
        # Remove common bank description noise characters for matching
        clean = p.replace("*", " ").replace(";", " ").replace("  ", " ").strip()
        
        # 1. Revenue & Inbound Payouts (Specific to The Reference App & LDK)
        if any(x in clean for x in [
            "google play", "play apps", "apple store", "itunes", "app store", 
            "stripe", "paypal", "revenue", "merchant payout", "customer payment"
        ]):
            return "Revenue"

        # 2. Capital Contributions & Transfers
        if any(x in clean for x in [
            "transfer from another bank", "elevations credit union", "account verification",
            "capital contribution", "founder funding"
        ]):
            return "Transfer"

        # 3. Legal, Professional, Compliance & State Filings
        if any(x in clean for x in [
            "corporate filings", "zenbusiness", "registered agent", "secretary of state",
            "franchise tax", "legal", "cpa", "accounting", "attorney"
        ]):
            return "Legal & Professional Services"

        # 4. Developer Tools, Cloud Infrastructure & SaaS
        if any(x in clean for x in [
            "github", "anthropic", "claude", "openai", "cursor", "cloudflare",
            "google cloud", "google workspace", "workspace_ldk", "aws", "amazon web",
            "vercel", "supabase", "digitalocean", "namecheap", "porkbun", "godaddy"
        ]):
            return "Software & Subscriptions"

        # 5. Marketing & Paid User Acquisition
        if any(x in clean for x in [
            "google ads", "google adwords", "search ads", "apple search ads",
            "meta ads", "facebook ads", "reddit ads"
        ]):
            return "Marketing & Advertising"

        # 6. Meals & Travel (Official Mercury Category Names)
        if any(x in clean for x in ["starbucks", "mcdonald", "chipotle", "restaurant", "cafe", "coffee", "lunch"]):
            return "Business Meals"
        if any(x in clean for x in ["uber", "lyft", "taxi", "airline", "hotel", "delta", "united"]):
            return "Travel & Transportation"

        # 7. Fallback matches
        if "google" in clean and ("ads" in clean or "adwords" in clean):
            return "Marketing & Advertising"
        if "google" in clean:
            return "Software & Subscriptions"

        return "Software & Subscriptions"

    def categorize(self, description: str) -> str:
        """
        Categorizes a transaction description using LLM-driven reasoning if available,
        falling back to high-accuracy domain rules aligned with Mercury Books.
        """
        if self.llm_client:
            prompt = self._build_prompt(description)
            try:
                return self.llm_client.complete(prompt).strip()
            except Exception:
                pass
        return self._rule_based_categorize(description)


if __name__ == "__main__":
    cat = TransactionCategorizer()
    test_cases = [
        ("Google Play", "Revenue"),
        ("Google Cloud", "Software & Subscriptions"),
        ("Google Workspace", "Software & Subscriptions"),
        ("Corporate Filings LLC", "Legal & Professional Services"),
        ("Elevations Credit Union", "Transfer"),
        ("Apple Search Ads", "Marketing & Advertising"),
        ("Starbucks", "Business Meals"),
        ("Uber", "Travel & Transportation"),
    ]
    for desc, expected in test_cases:
        res = cat.categorize(desc)
        print(f"[{'PASS' if res == expected else 'FAIL'}] {desc} -> {res} (Expected: {expected})")

