
from typing import List, Dict, Any

class TransactionCategorizer:
    def __init__(self, llm_client=None):
        """
        Initializes the categorizer.
        
        :param llm_client: An optional LLM client that implements a `complete(prompt: str) -> str` method.
        """
        self.llm_client = llm_client
        self.prompt_template = (
            "You are a financial assistant. Categorize the following transaction description "
            "into one of these categories: [Software & Subscriptions, Meals & Entertainment, "
            "Travel, Infrastructure, Revenue, Miscellaneous].\n\n"
            "Transaction: {description}\n\n"
            "Category:"
        )

    def _build_prompt(self, description: str) -> str:
        return self.prompt_template.format(description=description)

    def _get_llm_response(self, prompt: str) -> str:
        """
        Simulates or performs an LLM call to get the category.
        """
        if self.llm_client:
            return self.llm_client.complete(prompt).strip()
        
        p = prompt.lower()
        # Remove common bank description noise characters for matching
        clean = p.replace("*", " ").replace(";", " ").replace("  ", " ")
        clean = clean.strip()
        # Mapping logic - order matters: most specific first
        if any(x in clean for x in ["github", "anthropic", "claude"]):
            return "Software & Subscriptions"
        if "cloudflare" in clean:
            return "Software & Subscriptions"
        if "google workspace" in clean:
            return "Software & Subscriptions"
        if "google cloud" in clean:
            return "Software & Subscriptions"
        if "google ads" in clean:
            return "Marketing & Advertising"
        if "zenbusiness" in clean:
            return "Software & Subscriptions"
        if "itch" in clean:
            return "Miscellaneous"
        if any(x in clean for x in ["starbucks", "mcdonald", "chipotle", "restaurant"]):
            return "Meals & Entertainment"
        if any(x in clean for x in ["uber", "lyft", "taxi"]):
            return "Travel"
        if any(x in clean for x in ["stripe", "paypal", "venmo", "payment received"]):
            return "Revenue"
        if "google" in clean:
            return "Marketing & Advertising"
        return "Miscellaneous"

    def categorize(self, description: str) -> str:
        """
        Categorizes a transaction description using LLM-driven reasoning.
        """
        prompt = self._build_prompt(description)
        return self._get_llm_response(prompt)

if __name__ == "__main__":
    cat = TransactionCategorizer()
    print(f"Test 1: {cat.categorize('Google Workspace')}")
    print(f"Test 2: {cat.categorize('Google')}")
    print(f"Test 3: {cat.categorize('GitHub')}")
    print(f"Test 4: {cat.categorize('Anthropic')}")
    print(f"Test 5: {cat.categorize('Cloudflare')}")
    print(f"Test 6: {cat.categorize('Google Cloud')}")
    print(f"Test 7: {cat.categorize('Starbucks')}")
    print(f"Test 8: {cat.categorize('Uber')}")
    print(f"Test 9: {cat.categorize('Stripe')}")
    print(f"Test 10: {cat.categorize('Miscellaneous Item')}")
