# To store categorization rules and keywords

# config.py
# This file contains the categorization rules for transactions.
# You can easily add, remove, or modify categories and their associated keywords.

# The key is the category name that will be displayed in the dashboard.
# The value is a list of keywords to search for in the transaction description (Narration).
# The search is case-insensitive.

CATEGORY_RULES = {
    'Family & Personal': [
        'SAVITA SAXENA', 'SHUBH SAXENA', 'NEELAKSH'
    ],
    'Dine Outs': [
        'ZOMATO', 'SWIGGY', 'RESTAURANT', 'CAFE', 'STARBUCKS'
    ],
    'Shopping': [
        'BLINKIT', 'AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'ZARA', 'VYAPAR', 'POS'
    ],
    'Travel': [
        'UBER', 'OLA', 'IRCTC', 'REDBUS', 'MAKEMYTRIP', 'FLIGHT', 'GOIBIBO'
    ],
    'Entertainment': [
        'NETFLIX', 'SPOTIFY', 'PRIME VIDEO', 'BOOKMYSHOW', 'PVR', 'SONYLIV'
    ],
    'Health & Wellness': [
        'PHARMEASY', '1MG', 'GYM', 'HOSPITAL', 'DOCTOR'
    ],
    'Utilities & Bills': [
        'ELECTRICITY', 'BILL', 'VODAFONE', 'AIRTEL', 'JIO', 'GAS'
    ],
    'API Hostings': [
        'AWS', 'RENDER', 'DIGITALOCEAN', 'HEROKU', 'GCP', 'AZURE'
    ],
    'Software Tools': [
        'JETBRAINS', 'GITHUB', 'FIGMA', 'ADOBE', 'CANVA'
    ],
    'Cash Withdrawal': [
        'ATM', 'CASH WDL'
    ],
    'Investments': [
        'ZERODHA', 'GROWW', 'UPSTOX', 'MUTUAL FUND', 'SIP'
    ],
    # Add more categories and keywords as needed.
    # For example:
    # 'Groceries': ['BIGBASKET', 'GROFERS', 'DMART'],
    # 'Education': ['UDEMY', 'COURSERA', 'SCHOOL', 'COLLEGE'],
}

# Rules to identify the method of payment.
PAYMENT_METHOD_RULES = {
    'UPI': ['UPI'],
    'Card': ['POS', 'DEBIT CARD'],
    'Net Banking': ['NEFT', 'RTGS', 'IMPS'],
}
