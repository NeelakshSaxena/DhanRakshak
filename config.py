# config.py
# This file now contains a simple list of expected categories.
# The complex categorization logic is now handled by the AI enricher.

# This list helps maintain a consistent order and color scheme in charts.
EXPECTED_CATEGORIES = [
    'Shopping',
    'Food',
    'Entertainment',
    'Travel',
    'Utilities',
    'Health & Wellness',
    'Investments',
    'Security Net',
    'Self Transfer',
    'Family & Personal',
    'Miscellaneous',
    'Income'
]

# We can keep payment method rules here as they are simple and reliable
PAYMENT_METHOD_RULES = {
    'UPI': ['UPI'],
    'Card': ['POS', 'DEBIT CARD'],
    'Net Banking': ['NEFT', 'RTGS', 'IMPS'],
    'Cash': ['CASH DEPOSIT', 'ATM', 'CASH WDL']
}
