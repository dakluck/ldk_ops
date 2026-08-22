import unittest
from core.categorizer import TransactionCategorizer

class TestTransactionCategorizer(unittest.TestCase):
    def setUp(self):
        self.categorizer = TransactionCategorizer()

    def test_categorize_google_cloud(self):
        # The requirement specifically asked for this test case
        self.assertEqual(self.categorizer.categorize('Google CLOUD 4N2GJZ'), 'Software & Subscriptions')

    def test_categorize_starbucks(self):
        self.assertEqual(self.categorizer.categorize('Starbucks Coffee'), 'Meals & Entertainment')

    def test_categorize_uber(self):
        self.assertEqual(self.categorizer.categorize('Uber Trip'), 'Travel')

    def test_categorize_stripe(self):
        self.assertEqual(self.categorizer.categorize('Stripe Payout'), 'Revenue')

    def test_categorize_miscellaneous(self):
        self.assertEqual(self.categorizer.categorize('Unknown Store 123'), 'Miscellaneous')

if __name__ == '__main__':
    unittest.main()
