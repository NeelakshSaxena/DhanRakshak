# processor.py
# This file contains the core logic for processing the bank statement.
# This version adds detailed information extraction from the narration column.

import pandas as pd
from config import CATEGORY_RULES, PAYMENT_METHOD_RULES
import re
import streamlit as st
import io
import time

def load_data(uploaded_file):
    """
    Loads data from an uploaded text file (.txt, .csv). This function is
    designed for clean, text-based bank statements and is more reliable
    than trying to parse fake Excel files.
    """
    try:
        # Read the file as text, which is the correct method for .txt files
        uploaded_file.seek(0)
        raw_text = uploaded_file.getvalue().decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        uploaded_file.seek(0)
        raw_text = uploaded_file.getvalue().decode('latin-1')
    except Exception as e:
        raise ValueError(f"Failed to read the text file. Error: {e}")

    lines = raw_text.strip().split('\n')

    # Find the actual header row in the loaded data
    header_row_index = -1
    # Keywords tailored for the provided .txt file format
    header_keywords = ['Date', 'Narration', 'Debit Amount', 'Credit Amount']

    for i, line in enumerate(lines):
        # Check if the line contains all the necessary header keywords
        if all(keyword in line for keyword in header_keywords):
            header_row_index = i
            break

    if header_row_index == -1:
        raise ValueError("Could not automatically find the transaction header row within the text file.")

    # Create a new string containing only the relevant lines (from header onwards)
    relevant_text = "\n".join(lines[header_row_index:])
    string_io = io.StringIO(relevant_text)

    # Let pandas parse this cleaner text
    try:
        # Use a flexible regex separator to handle inconsistent spacing around commas
        df = pd.read_csv(
            string_io,
            sep=r'\s*,\s*', # Regex for comma surrounded by optional whitespace
            engine='python',
            on_bad_lines='warn' # Warn about bad lines instead of erroring
        )
    except Exception as e:
        raise ValueError(f"Pandas failed to parse the file. Error: {e}")

    if df.empty:
        raise ValueError("Pandas parsed the file, but no valid data rows were found.")

    # Standardize column names
    column_map = {
        'date': ['Date'],
        'description': ['Narration'],
        'debit': ['Debit Amount'],
        'credit': ['Credit Amount'],
    }
    
    rename_dict = {}
    for col_name in df.columns:
        stripped_col = str(col_name).strip()
        for std_name, variations in column_map.items():
            if stripped_col in variations:
                rename_dict[col_name] = std_name
                break
    df.rename(columns=rename_dict, inplace=True)

    # Drop unnecessary columns that might have been read
    required_cols = ['date', 'description', 'debit', 'credit']
    df = df[[col for col in required_cols if col in df.columns]]

    if 'date' not in df.columns or 'description' not in df.columns:
        found_cols = ", ".join(df.columns)
        raise ValueError(f"Failed to map essential columns. Found columns: [{found_cols}].")

    return df


def clean_data_types(df):
    """
    Cleans the DataFrame by converting columns to the correct data types.
    """
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)

    if 'debit' not in df.columns:
        df['debit'] = 0.0
    if 'credit' not in df.columns:
        df['credit'] = 0.0

    for col in ['debit', 'credit']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.fillna({'debit': 0, 'credit': 0, 'description': 'No Description'}, inplace=True)
    df.dropna(subset=['date'], inplace=True)
    return df

def extract_transaction_details(df):
    """
    Extracts detailed information like Merchant, Gateway, and Remarks
    from the complex 'description' column using regular expressions.
    """
    def parse_description(description):
        # Default values
        merchant = "N/A"
        gateway = "N/A"
        remark = ""

        # Pattern for UPI transactions
        upi_match = re.search(r'UPI-([^/-]+)-([^/-]+)', description)
        if upi_match:
            merchant = upi_match.group(1).strip()
            # Try to find gateway from the VPA
            vpa_match = re.search(r'@([a-zA-Z0-9]+)', upi_match.group(2))
            if vpa_match:
                gateway = vpa_match.group(1).upper()
            else:
                gateway = "UPI"
            # Try to find a remark at the end
            remark_match = re.search(r'-(.+)$', description)
            if remark_match and len(remark_match.group(1)) > 4: # Avoid short codes
                remark = remark_match.group(1).strip()
            return merchant, gateway, remark
        
        # Pattern for POS transactions
        pos_match = re.search(r'POS\s\d+X+\d+\s(.+)', description)
        if pos_match:
            merchant = pos_match.group(1).strip()
            gateway = "Card"
            return merchant, gateway, remark

        # Fallback for other types
        merchant = description[:40] # Truncate long descriptions
        return merchant, gateway, remark

    # Apply the parsing function to the description column
    details = df['description'].apply(parse_description)
    df[['merchant', 'gateway', 'remark']] = pd.DataFrame(details.tolist(), index=df.index)
    
    return df


def categorize_transactions(df):
    """
    Categorizes transactions based on the rules defined in config.py.
    """
    def get_category(description, rules):
        description = str(description).lower()
        for category, keywords in rules.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', description, re.IGNORECASE) or keyword.lower() in description:
                    return category
        return None

    df['category'] = df.apply(
        lambda row: get_category(row['description'], CATEGORY_RULES) if row['debit'] > 0 else 'Income',
        axis=1
    )
    df['payment_method'] = df['description'].apply(lambda x: get_category(x, PAYMENT_METHOD_RULES))
    df['category'] = df.apply(
        lambda row: 'Miscellaneous' if row['category'] is None and row['debit'] > 0 else row['category'],
        axis=1
    )
    df.fillna({'category': 'Miscellaneous', 'payment_method': 'Other'}, inplace=True)
    return df


def process_statement(uploaded_file, status):
    """
    Main processing pipeline that provides status updates.
    """
    status.update(label="Step 1/4: Reading text file...", state="running")
    time.sleep(1)
    df = load_data(uploaded_file)
    
    status.update(label="Step 2/4: Cleaning data...", state="running")
    time.sleep(1)
    df = clean_data_types(df)
    
    status.update(label="Step 3/4: Extracting details...", state="running")
    time.sleep(1)
    df = extract_transaction_details(df)

    status.update(label="Step 4/4: Categorizing transactions...", state="running")
    time.sleep(1)
    df = categorize_transactions(df)
    
    return df
