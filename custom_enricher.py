# custom_enricher.py
# This file uses a custom API endpoint (e.g. Runpod serverless) to enrich transaction data.

import requests
import json
import re
from user_mapping_store import load_user_mappings, find_mapping_for_description, build_dynamic_remark
from transaction_patterns import parse_rule_based_pattern

def extract_and_fix_json(content_str):
    """Extract JSON array from text and fix quote inconsistencies."""
    # Remove markdown code blocks if present
    if "```json" in content_str:
        content_str = content_str.split("```json")[1].split("```")[0]
    elif "```" in content_str:
        content_str = content_str.split("```")[1].split("```")[0]

    # Find the JSON array boundaries
    start_idx = content_str.find('[')
    end_idx = content_str.rfind(']')
    
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise ValueError("No valid JSON array found in response")

    json_str = content_str[start_idx:end_idx + 1]

    # Fix single quotes to double quotes, but carefully
    json_str = re.sub(r":\s*'([^']*)'([\s]*[,\}])", r': "\1"\2', json_str)
    json_str = re.sub(r"'([^']*)'([\s]*:)", r'"\1"\2', json_str)
    json_str = json_str.replace("'null'", 'null')

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        json_str_fixed = json_str.replace("'", '"')
        try:
            return json.loads(json_str_fixed)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse JSON even after quote fixes. Error: {e}. Content:\n{json_str[:500]}")

def enrich_with_custom(df, api_url, api_key, account_holder_name):
    """
    Sends transaction data to a custom model endpoint (like Runpod vLLM) for intelligent analysis.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    user_mappings = load_user_mappings()
    pre_mapped_results = []
    remaining_df = []

    for _, row in df.iterrows():
        desc = row.get('description', '') or row.get('narration', '')
        desc = str(desc)

        rule_parsed = parse_rule_based_pattern(desc)
        if rule_parsed:
            pre_mapped_results.append(rule_parsed)
            continue

        user_rule = find_mapping_for_description(desc, user_mappings)

        if user_rule:
            pre_mapped_results.append(
                {
                    "original_description": desc,
                    "category": user_rule.get("category", "Shopping"),
                    "remark": build_dynamic_remark(desc, user_rule.get("remark", "General Purchase / Transaction")),
                    "transaction_type": "", "subcategory": "", "amount_direction": "",
                    "entities": {"merchant": "", "organization": "", "upi_id": ""},
                    "metadata": {"reference_number": "", "date": "", "time": "", "location": ""},
                    "explanation": "Applied saved user narration rule",
                }
            )
        else:
            remaining_df.append(row)

    if not remaining_df:
        return pre_mapped_results

    remaining_df = df.__class__(remaining_df)
    batch_size = 15  
    all_results = []
    
    for batch_idx in range(0, len(remaining_df), batch_size):
        batch_df = remaining_df.iloc[batch_idx:batch_idx + batch_size]
        transactions = []
        for idx, row in batch_df.iterrows():
            desc = row.get('description', '') or row.get('narration', '')
            transactions.append({'d': str(desc)})
        
        transactions_json = json.dumps(transactions)

        prompt = f"""You are a financial transaction categorizer. Analyze these transactions and return ONLY a valid JSON array with double quotes. Match the original description exactly. Do not use markdown blocks.

Return ONLY this format:
[
  {{
    "original_description": "...",
    "category": "...",
    "remark": "...",
    "transaction_type": "",
    "subcategory": "",
    "amount_direction": "",
    "entities": {{"merchant": "", "organization": "", "upi_id": ""}},
    "metadata": {{"reference_number": "", "date": "", "time": "", "location": ""}},
    "explanation": ""
  }}
]

CATEGORIZATION RULES:
- If text contains "{account_holder_name}", category: "Family & Personal", remark: "Personal transfer"
- "swiggy" or "zomato" -> category: "Food & Dining"
- "amazon" or "flipkart" -> category: "Shopping"
- Default category: "Shopping", remark: "General Purchase/Transaction"
- NEVER return blank category or remark.
- ALWAYS return all fields.

Transactions to analyze: {transactions_json}

Output ONLY the JSON array.
"""

        payload = {
            "input": {
                "prompt": prompt
            }
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Flexible parsing of runpod style response
            content_str = ""
            if 'output' in result:
                if isinstance(result['output'], str):
                    content_str = result['output']
                elif isinstance(result['output'], list) and len(result['output']) > 0 and isinstance(result['output'][0], str):
                    content_str = result['output'][0]
                else:
                    content_str = json.dumps(result['output'])
            elif 'text' in result:
                content_str = result['text']
            elif 'choices' in result: # Fallback to OpenAI style just in case
                content_str = result['choices'][0].get('message', {}).get('content', '') or result['choices'][0].get('text', '')
            else:
                content_str = json.dumps(result)
            
            batch_results = extract_and_fix_json(content_str)
            
            for res in batch_results:
                if not res.get('category') or res.get('category').strip() == '':
                    res['category'] = 'Shopping'
                if not res.get('remark') or res.get('remark').strip() == '':
                    res['remark'] = 'General Purchase / Transaction'
                for field in ['transaction_type', 'subcategory', 'amount_direction', 'explanation']:
                    if field not in res: res[field] = ''
                if 'entities' not in res or not isinstance(res.get('entities'), dict):
                    res['entities'] = {"merchant": "", "organization": "", "upi_id": ""}
                if 'metadata' not in res or not isinstance(res.get('metadata'), dict):
                    res['metadata'] = {"reference_number": "", "date": "", "time": "", "location": ""}
            
            all_results.extend(batch_results)
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Could not connect to the Custom Endpoint at {api_url}. Error: {e}")
        except ValueError as e:
            raise RuntimeError(f"Failed to extract valid JSON from the Custom Endpoint model. Error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected response format from Custom Endpoint. Error: {e}.")
    
    return pre_mapped_results + all_results
