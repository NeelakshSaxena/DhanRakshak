# processor.py
# This file contains the core logic for processing the bank statement.
# This version conditionally imports the correct AI enricher.

import pandas as pd
from config import PAYMENT_METHOD_RULES
import re
import streamlit as st
import io
import time
import csv
import json
from user_mapping_store import apply_user_mappings_to_df
from transaction_patterns import apply_pattern_enrichment
from transaction_modes import apply_transaction_modes


def detect_delimiter(sample_text):
    """Try to detect delimiter automatically with csv.Sniffer and fallback list."""
    potential = [',', '\t', '|', ';']
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=potential)
        if dialect.delimiter:
            return dialect.delimiter
    except Exception:
        pass

    counts = {d: sample_text.count(d) for d in potential}
    best = max(counts, key=counts.get)
    if counts[best] > 0:
        return best
        
    # If standard delimiters aren't found, check for fixed-width (multiple spaces)
    if sample_text.count('  ') > 5:
        return 'fwf'
        
    return ','


def find_header_row(lines):
    """Find header row index by matching known fields."""
    header_tokens = ['date', 'narration', 'chq', 'ref', 'value', 'withdrawal', 'deposit', 'closing']

    for i, line in enumerate(lines):
        low = line.lower()
        if 'date' in low and 'narration' in low:
            return i

    for i, line in enumerate(lines):
        low = line.lower()
        if any(tok in low for tok in header_tokens):
            return i

    return -1


def normalize_column_name(col_name):
    std = re.sub(r'[\W_]+', ' ', str(col_name).strip().lower())
    std = ' '.join(std.split())

    if std in ['date', 'transaction date', 'txn date']:
        return 'date'
    if std in ['value date', 'value_date', 'value dt', 'value dt.']:
        return 'value_date'
    if std in ['narration', 'description', 'particulars', 'remarks', 'transaction details']:
        return 'narration'
    if 'ref' in std or 'chq' in std or 'cheque' in std or 'tranid' in std or 'reference' in std:
        return 'reference'
    if 'withdrawal' in std or 'debit' in std or 'dr amount' in std or 'withdraw' in std:
        return 'withdrawal_amount'
    if 'deposit' in std or 'credit' in std or 'cr amount' in std:
        return 'deposit_amount'
    if 'closing' in std or 'balance' in std or 'closing balance' in std:
        return 'closing_balance'
    return None


def load_data(file_or_text, use_ai_mapper=False, ai_provider=None, api_config=None):
    """Loads data from an uploaded text file (.txt, .csv) or raw text string, and normalizes columns."""
    is_excel = hasattr(file_or_text, 'name') and file_or_text.name.lower().endswith(('.xlsx', '.xls'))
    
    if is_excel:
        try:
            file_or_text.seek(0)
            temp_df = pd.read_excel(file_or_text, header=None)
            lines = temp_df.apply(lambda row: ' '.join(row.dropna().astype(str)), axis=1).tolist()
            header_row_index = find_header_row(lines)
            
            if header_row_index == -1:
                if use_ai_mapper:
                    header_row_index = 0
                else:
                    raise ValueError("Could not automatically find the transaction header row in the Excel file.")
            
            file_or_text.seek(0)
            df = pd.read_excel(file_or_text, header=header_row_index)
            sample_text = df.head(5).to_csv(index=False)
        except Exception as e:
            raise ValueError(f"Failed to parse the Excel file. Error: {e}")
            
    else:
        if isinstance(file_or_text, str):
            raw_text = file_or_text
        elif hasattr(file_or_text, 'getvalue'):
            file_or_text.seek(0)
            try:
                raw_text = file_or_text.getvalue().decode('utf-8')
            except UnicodeDecodeError:
                file_or_text.seek(0)
                raw_text = file_or_text.getvalue().decode('latin-1')
        else:
            raise ValueError(f"Input to load_data must be a string or a file-like object, got {type(file_or_text)}")
    
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        if not lines:
            raise ValueError("Uploaded file is empty or only whitespace.")
    
        header_row_index = find_header_row(lines)
        if header_row_index == -1:
            if use_ai_mapper:
                header_row_index = 0
            else:
                raise ValueError("Could not automatically find the transaction header row within the text file.")
    
        sample_text = '\n'.join(lines[header_row_index:header_row_index + 5])
        delimiter = detect_delimiter(sample_text)
    
        table_text = '\n'.join(lines[header_row_index:])
        try:
            if delimiter == 'fwf':
                df = pd.read_fwf(
                    io.StringIO(table_text),
                    skipinitialspace=True
                )
            else:
                df = pd.read_csv(
                    io.StringIO(table_text),
                    sep=delimiter,
                    engine='python',
                    skipinitialspace=True,
                    on_bad_lines='warn'
                )
        except Exception as e:
            raise ValueError(f"Pandas failed to parse the CSV/Text file. Error: {e}")

    if df.empty:
        raise ValueError("Pandas parsed the file, but no valid data rows were found.")

    df.attrs['original_columns'] = list(df.columns)
    
    needed = ['date', 'narration', 'reference', 'value_date', 'withdrawal_amount', 'deposit_amount', 'closing_balance']
    
    mapping_applied = False
    
    # Try AI Mapping first if requested
    if use_ai_mapper and ai_provider and api_config:
        st.info("🧠 Asking AI to understand the statement format...")
        from ai_schema_mapper import get_ai_column_mapping
        ai_mapping = get_ai_column_mapping(sample_text, ai_provider, api_config)
        if ai_mapping:
            for orig_col, target_col in ai_mapping.items():
                # Fuzzy match column name in case AI slightly hallucinates whitespace
                matched_cols = [c for c in df.columns if c.strip().lower() == str(orig_col).strip().lower()]
                if matched_cols and target_col in needed:
                    df[target_col] = df[matched_cols[0]]
                    mapping_applied = True
            if mapping_applied:
                st.success("✅ AI successfully mapped the statement columns!")
    
    # Fallback to dictionary matching if AI wasn't used or failed
    if not mapping_applied:
        for col in df.columns:
            normalized = normalize_column_name(col)
            if normalized:
                if normalized not in df.columns:
                    df[normalized] = df[col]

    for col in needed:
        if col not in df.columns:
            df[col] = pd.NA

    # --- Wrapped Row Merging Logic ---
    # In FWF, wrapped lines usually have no Date, but they do have Narration text.
    if 'date' in df.columns and 'narration' in df.columns:
        # A main row is one that has a date
        is_main_row = df['date'].notna() & (df['date'].astype(str).str.strip() != '') & (df['date'].astype(str).str.strip().str.lower() != 'nan')
        if not is_main_row.all() and is_main_row.any():
            # Group ID increments on every main row
            df['group_id'] = is_main_row.cumsum()
            
            # Filter out any garbage rows before the first valid date (group_id = 0)
            df = df[df['group_id'] > 0]
            
            # Aggregate: Take first non-null for most columns, but join text for narration
            agg_funcs = {col: 'first' for col in df.columns if col not in ['group_id', 'narration']}
            agg_funcs['narration'] = lambda x: ' '.join(x.dropna().astype(str).str.strip())
            
            df = df.groupby('group_id').agg(agg_funcs).reset_index(drop=True)

    df = df[~df[needed].isna().all(axis=1)]

    return df


def clean_data_types(df):
    """Cleans dataframe values and normalizes types."""
    for text_col in ['narration', 'reference']:
        if text_col in df.columns:
            df[text_col] = df[text_col].astype(str).str.strip().replace({'nan': pd.NA})

    for date_col in ['date', 'value_date']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
            df[date_col] = df[date_col].dt.strftime('%Y-%m-%d')

    def clean_number(val):
        if pd.isna(val):
            return pd.NA
        s = str(val).strip()
        if s == '':
            return pd.NA
        s = re.sub(r'[₹$\s(),]', '', s)
        s = s.replace(',', '')
        try:
            return float(s)
        except Exception:
            return pd.NA

    for num_col in ['withdrawal_amount', 'deposit_amount', 'closing_balance']:
        if num_col in df.columns:
            df[num_col] = df[num_col].apply(clean_number)

    if 'date' in df.columns:
        df = df.dropna(subset=['date'], how='all')

    df = df.where(pd.notnull(df), None)
    return df


def get_payment_method(df):
    """Determines payment method using setup rules."""
    def get_method(description):
        description = str(description).lower()
        for method, keywords in PAYMENT_METHOD_RULES.items():
            for keyword in keywords:
                if keyword.lower() in description:
                    return method
        return 'Other'

    df['payment_method'] = df['narration'].fillna('') .apply(get_method) if 'narration' in df.columns else 'Other'
    return df


def statement_df_to_json(df):
    """Convert normalized DataFrame to required JSON output schema."""
    schema_cols = ['date', 'narration', 'reference', 'value_date', 'withdrawal_amount', 'deposit_amount', 'closing_balance']
    out_df = df.copy()
    for col in schema_cols:
        if col not in out_df.columns:
            out_df[col] = None
    out_df = out_df[schema_cols]
    records = out_df.to_dict(orient='records')
    return json.dumps(records, ensure_ascii=False, indent=2)


def process_statement(uploaded_file, account_holder_name, ai_provider, api_config, force_skip_ai=False, use_ai_mapper=False):
    """Main processing pipeline - preserves original narration, adds category/remark."""
    df = load_data(uploaded_file, use_ai_mapper=use_ai_mapper, ai_provider=ai_provider, api_config=api_config)
    original_cols = df.attrs.get('original_columns', [])
    
    df = clean_data_types(df)

    # preserve legacy names
    if 'description' not in df.columns and 'narration' in df.columns:
        df['description'] = df['narration']
    if 'debit' not in df.columns and 'withdrawal_amount' in df.columns:
        df['debit'] = df['withdrawal_amount']
    if 'credit' not in df.columns and 'deposit_amount' in df.columns:
        df['credit'] = df['deposit_amount']

    # Check if this is an already processed statement or user forces skip
    is_pre_processed = force_skip_ai or ('category' in df.columns)

    if not is_pre_processed:
        if ai_provider == 'Gemini API':
            from gemini_enricher import enrich_with_gemini
            enriched_data = enrich_with_gemini(df, api_config['key'], account_holder_name, api_config.get('model', 'gemini-1.5-flash'))
        elif ai_provider == 'Local Server':
            from local_ai_enricher import enrich_with_local_llama
            enriched_data = enrich_with_local_llama(df, api_config['url'], account_holder_name)
        elif ai_provider == 'Custom Endpoint':
            from custom_enricher import enrich_with_custom
            enriched_data = enrich_with_custom(df, api_config['url'], api_config['key'], account_holder_name)
        else:
            raise ValueError('Invalid AI Provider specified.')
    
        # Merge enriched data - get category and remark only
        enriched_df = pd.DataFrame(enriched_data)
        if enriched_df.shape[0] > 0:
            # Avoid many-to-many row explosions if description repeats.
            if 'original_description' in enriched_df.columns:
                enriched_df = enriched_df.drop_duplicates(subset=['original_description'], keep='last')
    
            desc_col = 'description' if 'description' in df.columns else 'narration'
            df = pd.merge(df, enriched_df, left_on=desc_col, right_on='original_description', how='left')
            df.drop(columns=['original_description'], inplace=True, errors='ignore')

    # Merchant stays as original narration (never blank)
    if 'merchant' not in df.columns:
        df['merchant'] = df.get('description', df.get('narration', ''))
    df['merchant'] = df['merchant'].fillna(df.get('description', df.get('narration', '')))

    # Apply deterministic pattern parser for both Gemini API and Local LLM outputs.
    df = apply_pattern_enrichment(df, description_col='description')

    # User-saved rules are always authoritative for category/remark.
    df = apply_user_mappings_to_df(df, description_col='description')

    # Determine India transaction mode for each row using statement text.
    df = apply_transaction_modes(df, description_col='description')

    df = get_payment_method(df)
    df['category'] = df['category'].fillna('Shopping')
    df['remark'] = df['remark'].fillna('')
    
    # Restore original_columns attribute as Pandas operations likely dropped it
    df.attrs['original_columns'] = original_cols
    df.attrs['is_pre_processed'] = is_pre_processed
    
    return df
