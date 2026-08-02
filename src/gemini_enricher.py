# gemini_enricher.py
# This file contains the logic to call the Google Gemini API.

import requests
import json

def enrich_with_gemini(df, api_key, account_holder_name, model_name="gemini-1.5-flash"):
    """
    Sends transaction data to the Google Gemini API for analysis.
    """
    # Clean the API key to remove whitespace or unwanted characters
    cleaned_api_key = api_key.strip().strip("'\"")
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={cleaned_api_key}"
    
    transactions_json = df[['description', 'debit', 'credit']].to_json(orient='records')
    json_schema = {
        "type": "ARRAY", "items": {
            "type": "OBJECT", "properties": {
                "original_description": {"type": "STRING"}, "merchant": {"type": "STRING"},
                "category": {"type": "STRING"}, "remark": {"type": "STRING"}
            }, "required": ["original_description", "merchant", "category", "remark"]
        }
    }
    prompt = f"""
You are a highly intelligent financial analyst AI. Your task is to analyze the following list of bank transactions and enrich them according to the user's custom rules. The account holder's name is "{account_holder_name}".

**Analysis Rules:**
1.  **Merchant Name:** Extract ONLY the primary merchant or recipient name. Be concise. For example:
    - From "UPI-MASTER NEELAKSH SAX-NEELAKSH7.SAXENA@OKSBI..." -> "MASTER NEELAKSH SAX"
    - From "POS 435584XXXXXX1876 BLINKIT" -> "BLINKIT"
    - From "UPI-DHINAKARAN K-PAYTMQRZ19AOZ75MM@PAYTM..." -> "DHINAKARAN K"
2.  **Categorization & Remarks:** Apply these rules:
    - Transaction to 'fampay' AND '{account_holder_name}' -> Category: 'Security Net', Remark: 'Transfer to Fampay'.
    - Transaction involving '{account_holder_name}' between different banks -> Category: 'Self Transfer', Remark: 'Inter-bank Self Transfer'.
    - Transaction to 'ALPHANUMERICALS' -> Category: 'Food', Remark: 'One Food World'.
    - Transaction to 'ICCL MUTUAL FUNDS' -> Category: 'Investments', Remark: 'SIP Installment'.
    - Transaction to 'INOX' or 'FDINOX' -> Category: 'Entertainment', Remark: 'INOX Movie'.
    - For all others, use your best judgment to assign a relevant category ('Shopping', 'Travel', 'Utilities', 'Family & Personal', 'Income') and a brief remark.

**Input Transactions (JSON format):**
{transactions_json}

Analyze these transactions and return a JSON array that matches the provided schema. The `original_description` in your output MUST match the `description` from the input exactly.
"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": json_schema}
    }
    headers = {'Content-Type': 'application/json'}
    import time
    import streamlit as st
    
    max_retries = 3
    base_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            enriched_data_str = result['candidates'][0]['content']['parts'][0]['text']
            return json.loads(enriched_data_str)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                st.warning(f"API Rate limit hit (429). Retrying in {delay} seconds... (Attempt {attempt+1}/{max_retries-1})")
                time.sleep(delay)
                continue
            raise RuntimeError(f"Network error calling Gemini API: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error calling Gemini API: {e}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to get valid JSON from Gemini API. Error: {e}. Response: {response.text}")
