# local_ai_enricher.py
# This file uses a local AI model (via LM Studio) to enrich transaction data.
# Original narration is preserved; categorization and insights go to remarks only.

import requests
import json
import re
from user_mapping_store import load_user_mappings, find_mapping_for_description, build_dynamic_remark


def extract_and_fix_json(content_str):
    """Extract JSON array from text and fix quote inconsistencies."""
    # Find the JSON array boundaries
    start_idx = content_str.find('[')
    end_idx = content_str.rfind(']')
    
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise ValueError("No valid JSON array found in response")
    
    json_str = content_str[start_idx:end_idx + 1]
    
    # Fix single quotes to double quotes, but carefully
    # Replace single quotes that are used as string delimiters (not within double-quoted strings)
    # Pattern: :[\s]*'([^']*)'([\s]*[,\}\]])
    json_str = re.sub(r":\s*'([^']*)'([\s]*[,\}])", r': "\1"\2', json_str)
    
    # Also handle cases like {'key': 'value'} at the start of fields
    json_str = re.sub(r"'([^']*)'([\s]*:)", r'"\1"\2', json_str)
    
    # Handle null values with single quotes turns like 'null'
    json_str = json_str.replace("'null'", 'null')
    
    # Try to parse and validate
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Last resort: try a more aggressive fix
        # Replace ALL remaining single quotes with double quotes
        json_str_fixed = json_str.replace("'", '"')
        try:
            return json.loads(json_str_fixed)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse JSON even after quote fixes. Error: {e}. Content:\n{json_str[:500]}")


def enrich_with_local_llama(df, api_url, account_holder_name):
    """
    Sends transaction data to a local Llama 3 model for intelligent analysis.
    Uses batch processing to maintain high-quality categorization.
    Preserves original narration; categorization/insight details go to remarks.
    """
    headers = {"Content-Type": "application/json"}
    user_mappings = load_user_mappings()

    # Apply user-saved mappings first so known narrations do not rely on LLM guesses.
    pre_mapped_results = []
    remaining_df = []

    for _, row in df.iterrows():
        desc = row.get('description', '') or row.get('narration', '')
        desc = str(desc)
        user_rule = find_mapping_for_description(desc, user_mappings)

        if user_rule:
            pre_mapped_results.append(
                {
                    "original_description": desc,
                    "category": user_rule.get("category", "Shopping"),
                    "remark": build_dynamic_remark(
                        desc,
                        user_rule.get("remark", "General Purchase / Transaction")
                    ),
                }
            )
        else:
            remaining_df.append(row)

    if not remaining_df:
        return pre_mapped_results

    remaining_df = df.__class__(remaining_df)
    
    # Process transactions in batches to avoid vague results
    batch_size = 15  # Optimal size for detailed categorization
    all_results = []
    
    for batch_idx in range(0, len(remaining_df), batch_size):
        batch_df = remaining_df.iloc[batch_idx:batch_idx + batch_size]
        transactions = []
        for idx, row in batch_df.iterrows():
            desc = row.get('description', '') or row.get('narration', '')
            transactions.append({'d': str(desc)})
        
        transactions_json = json.dumps(transactions)

        user_rules_text = ""
        if user_mappings:
            rule_lines = []
            for rule in user_mappings:
                pattern = str(rule.get("pattern", "")).strip()
                category = str(rule.get("category", "Shopping")).strip()
                remark = str(rule.get("remark", "General Purchase / Transaction")).strip()
                match_type = str(rule.get("match_type", "contains")).strip()
                if pattern:
                    rule_lines.append(
                        f'- {match_type} "{pattern}" -> category: "{category}", remark: "{remark}"'
                    )
            if rule_lines:
                user_rules_text = "\nUSER SAVED RULES (HIGH PRIORITY):\n" + "\n".join(rule_lines) + "\n"

        # Comprehensive prompt that returns category and remark only
        # Original description will be preserved from CSV
        prompt = f"""Analyze bank transactions and return their CATEGORY and REMARK ONLY.
Do NOT return a modified merchant name - the original transaction description is preserved as-is.

Return ONLY this JSON format: [{{original_description, category, remark}}]

CATEGORIZATION RULES (Apply in order - use the FIRST match):

1. TRANSFERS & SECURITY:
   - Contains "fampay" -> category: "Transfer" remark: "Transfer to Fampay/Security wallet"
   - Contains "imps" OR "neft" OR "rtgs" -> category: "Transfer" remark: "Bank Transfer"
   - Contains "{account_holder_name}" -> category: "Family & Personal" remark: "Personal transfer/movement"

2. INVESTMENTS & INSURANCE:
   - "ICCL" OR "mutual" -> category: "Investments" remark: "Mutual Fund SIP Installment"
   - "insurance" OR "premium" -> category: "Insurance" remark: "Insurance Premium Payment"
   - "lic" -> category: "Insurance" remark: "LIC Life Insurance"

3. ENTERTAINMENT:
   - "INOX" OR "FDINOX" OR "inox" -> category: "Entertainment" remark: "INOX Movie Ticket"
   - "movie" OR "cinema" OR "ticket" -> category: "Entertainment" remark: "Movie/Entertainment"
   - "bookmyshow" -> category: "Entertainment" remark: "Event Booking"

4. UTILITIES & SUBSCRIPTIONS:
   - "electricity" OR "power" OR "bill" -> category: "Utilities" remark: "Electricity/Utility Bill"
   - "water" -> category: "Utilities" remark: "Water Bill"
   - "phone" OR "recharge" OR "airtel" OR "jio" OR "vodafone" -> category: "Utilities" remark: "Mobile Phone Recharge"
   - "internet" OR "broadband" -> category: "Utilities" remark: "Internet/Broadband"
   - "subscription" OR "prime" OR "netflix" OR "spotify" -> category: "Subscriptions" remark: "Subscription Service"

5. FOOD & DINING:
   - "zomato" OR "swiggy" -> category: "Food & Dining" remark: "Food Delivery App"
   - "blinkit" -> category: "Shopping" remark: "Quick Commerce - Grocery/Essentials"
   - "cafe" OR "restaurant" OR "burger" OR "pizza" -> category: "Food & Dining" remark: "Restaurant/Cafe"

6. SHOPPING & RETAIL:
   - "amazon" OR "flipkart" -> category: "Shopping" remark: "Online Retail Shopping"
   - "myntra" -> category: "Shopping" remark: "Fashion/Clothing Shopping"
   - "mall" OR "store" OR "supermarket" -> category: "Shopping" remark: "Retail/Grocery Shopping"

7. TRAVEL & TRANSPORTATION:
   - "uber" OR "ola" -> category: "Travel" remark: "Ride Sharing/Taxi Service"
   - "booking" OR "hotel" -> category: "Travel" remark: "Hotel Booking"
   - "flight" OR "airline" OR "airasia" OR "indigo" -> category: "Travel" remark: "Flight Booking"
   - "petrol" OR "fuel" OR "gas station" -> category: "Transportation" remark: "Fuel/Petrol"

8. HEALTH & WELLNESS:
   - "hospital" OR "clinic" OR "doctor" OR "medical" -> category: "Healthcare" remark: "Medical/Doctor Visit"
   - "pharmacy" OR "medicine" -> category: "Healthcare" remark: "Medicine/Pharmacy"
   - "gym" OR "fitness" -> category: "Health & Wellness" remark: "Gym/Fitness Membership"

9. DEFAULT (ALWAYS use if no match):
   - No match -> category: "Shopping" remark: "General Purchase/Transaction"

CRITICAL REQUIREMENTS:
- NEVER return blank category or remark - always provide values
- ALWAYS return all three fields: original_description, category, remark
- remark should briefly describe what type of transaction this is (if unsure, default to category + general description)
- Do NOT modify or replace the original_description - return it exactly as provided

Transactions to analyze: {transactions_json}

{user_rules_text}

Output ONLY the JSON array with double quotes. No markdown, no explanations."""

        payload = {
            "messages": [
                {"role": "system", "content": "You are a financial transaction categorizer. Return ONLY a valid JSON array with double quotes. Never return blank fields. If unsure about a category, use 'Shopping' as default. Match the original description exactly. No markdown or code blocks."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.05,
            "max_tokens": 6000,
            "stream": False
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            content_str = result['choices'][0]['message']['content']
            
            # Remove markdown code blocks if present
            if "```json" in content_str:
                content_str = content_str.split("```json")[1].split("```")[0]
            elif "```" in content_str:
                content_str = content_str.split("```")[1].split("```")[0]
            
            # Extract and fix JSON array
            batch_results = extract_and_fix_json(content_str)
            
            # Ensure no blank values - add fallbacks
            for result in batch_results:
                if not result.get('category') or result.get('category').strip() == '':
                    result['category'] = 'Shopping'
                if not result.get('remark') or result.get('remark').strip() == '':
                    result['remark'] = 'General Purchase / Transaction'
            
            all_results.extend(batch_results)
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Could not connect to the local AI server at {api_url}. Is LM Studio running? Error: {e}")
        except ValueError as e:
            raise RuntimeError(f"Failed to extract valid JSON from the local model. Error: {e}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response format from local model. Error: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
    
    return pre_mapped_results + all_results
