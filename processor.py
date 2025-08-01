# processor.py
# This file contains the core logic for processing the bank statement.
# This version conditionally imports the correct AI enricher.

import pandas as pd
from config import PAYMENT_METHOD_RULES
import re
import streamlit as st
import io
import time

def load_data(uploaded_file):
    """
    Loads data from an uploaded text file (.txt, .csv).
    """
    try:
        uploaded_file.seek(0)
        raw_text = uploaded_file.getvalue().decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        uploaded_file.seek(0)
        raw_text = uploaded_file.getvalue().decode('latin-1')
    except Exception as e:
        raise ValueError(f"Failed to read the text file. Error: {e}")

    lines = raw_text.strip().split('\n')
    header_row_index = -1
    header_keywords = ['Date', 'Narration', 'Debit Amount', 'Credit Amount']

    for i, line in enumerate(lines):
        if all(keyword in line for keyword in header_keywords):
            header_row_index = i
            break

    if header_row_index == -1:
        raise ValueError("Could not automatically find the transaction header row within the text file.")

    relevant_text = "\n".join(lines[header_row_index:])
    string_io = io.StringIO(relevant_text)

    try:
        df = pd.read_csv(
            string_io,
            sep=r'\s*,\s*',
            engine='python',
            on_bad_lines='warn'
        )
    except Exception as e:
        raise ValueError(f"Pandas failed to parse the file. Error: {e}")

    if df.empty:
        raise ValueError("Pandas parsed the file, but no valid data rows were found.")

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


def get_payment_method(df):
    """
    Determines the payment method using simple keyword matching.
    """
    def get_method(description):
        description = str(description).lower()
        for method, keywords in PAYMENT_METHOD_RULES.items():
            for keyword in keywords:
                if keyword.lower() in description:
                    return method
        return 'Other'

    df['payment_method'] = df['description'].apply(get_method)
    return df


def process_statement(uploaded_file, account_holder_name, ai_provider, api_config):
    """
    Main processing pipeline that now conditionally imports the correct enricher.
    """
    # Step 1: Reading and parsing file
    df = load_data(uploaded_file)
    df = clean_data_types(df)
    
    # Step 2: Sending data to AI for analysis
    if ai_provider == "Gemini API":
        from gemini_enricher import enrich_with_gemini
        enriched_data = enrich_with_gemini(df, api_config['key'], account_holder_name)
    elif ai_provider == "Local Server":
        from local_ai_enricher import enrich_with_local_llama
        enriched_data = enrich_with_local_llama(df, api_config['url'], account_holder_name)
    else:
        raise ValueError("Invalid AI Provider specified.")

    # Step 3: Merging AI insights
    enriched_df = pd.DataFrame(enriched_data)
    
    df = pd.merge(
        df,
        enriched_df,
        left_on='description',
        right_on='original_description',
        how='left'
    )
    
    df.drop(columns=['original_description'], inplace=True, errors='ignore')

    # Step 4: Finalizing details
    df = get_payment_method(df)

    df.fillna({
        'merchant': df['description'], 
        'category': 'Miscellaneous', 
        'remark': ''
    }, inplace=True)

    return df
