import json
import requests
import streamlit as st
import time

def get_ai_column_mapping(sample_text, ai_provider, api_config):
    """
    Sends the first few rows of a statement to the AI and asks it to map 
    the original column headers to the required internal schema.
    """
    prompt = f"""
You are an intelligent data parser. I am providing you with the first few rows of a bank statement (CSV/TSV format).
Your job is to identify which column headers correspond to the following required fields:
- date: The date of the transaction
- narration: The description, remarks, or particulars
- reference: Reference number or cheque number (if exists, else null)
- withdrawal_amount: The money out, debit, or withdrawal amount
- deposit_amount: The money in, credit, or deposit amount
- closing_balance: The running balance

Here is the data sample:
{sample_text}

Return a JSON object where keys are the EXACT original column headers from the data, and the values are the corresponding required field names (date, narration, reference, withdrawal_amount, deposit_amount, closing_balance). If a required field doesn't exist in the data, do not include it. Only map columns that you are confident about.
"""

    if ai_provider == 'Gemini API':
        api_key = api_config.get('key', '').strip().strip("'\"")
        model_name = api_config.get('model', 'gemini-1.5-flash')
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"} # Omitting strict schema to allow dynamic keys
        }
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            mapping_str = result['candidates'][0]['content']['parts'][0]['text']
            return json.loads(mapping_str)
        except Exception as e:
            st.error(f"AI Mapping failed: {e}")
            return None
            
    elif ai_provider == 'Local Server':
        api_url = api_config.get('url', 'http://localhost:1234/v1/chat/completions')
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        try:
            response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            result = response.json()
            mapping_str = result['choices'][0]['message']['content']
            return json.loads(mapping_str)
        except Exception as e:
            st.error(f"Local AI Mapping failed: {e}")
            return None
    else:
        # Custom endpoint is unpredictable for schema tasks
        st.warning("AI Mapping is only supported for Gemini API and Local Server.")
        return None
