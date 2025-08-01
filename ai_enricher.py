# local_ai_enricher.py
# This file uses a local AI model (via LM Studio) to enrich transaction data.

import requests
import json

def enrich_with_local_llama(df, api_url, account_holder_name):
    """
    Sends transaction data to a local Llama 3 model for intelligent analysis.
    """
    headers = {"Content-Type": "application/json"}
    transactions_json = df[['description', 'debit', 'credit']].to_json(orient='records')

    prompt = f"""
You are an expert financial analyst. Your only job is to analyze a list of bank transactions and return a clean JSON array. The account holder's name is "{account_holder_name}".

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
    - For all others, use your best judgment to assign a category ('Shopping', 'Travel', 'Utilities', 'Family & Personal', 'Income') and a brief remark.

**Input Transactions:**
{transactions_json}

**Your Task:**
Provide a JSON array where each object contains: "original_description", "merchant", "category", and "remark". The `original_description` MUST EXACTLY MATCH the input description. Respond with ONLY the JSON array.
"""
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that only returns JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1, "stream": False
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content_str = result['choices'][0]['message']['content']
        if "```json" in content_str:
            content_str = content_str.split("```json")[1].split("```")[0]
        return json.loads(content_str.strip())
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Could not connect to the local AI server at {api_url}. Is LM Studio running? Error: {e}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to get valid JSON from the local model. Error: {e}. Model Response: {response.text}")
