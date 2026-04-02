import re
import pandas as pd


def parse_rule_based_pattern(description):
    """Deterministic parser for known high-confidence transaction patterns."""
    text = str(description or "").strip()
    if not text:
        return None

    upper_text = text.upper()

    # UPI Mutual Fund AutoPay pattern
    if "UPI" in upper_text and "MUTUAL FUNDS" in upper_text and "MFAUTOPAY" in upper_text:
        org_match = re.search(r"^UPI[- ]([^\-]+)", text, flags=re.IGNORECASE)
        upi_match = re.search(r"MFAUTOPAY\.([A-Z0-9._%+-]+@[A-Z0-9.-]+)", text, flags=re.IGNORECASE)
        ref_match = re.search(r"-(\d{8,})-", text)

        organization = org_match.group(1).strip() if org_match else "ICCL"
        upi_id = upi_match.group(1).lower() if upi_match else ""
        reference_number = ref_match.group(1) if ref_match else ""

        remark = "UPI AutoPay SIP"
        if upi_id:
            remark = f"UPI AutoPay SIP ({upi_id})"

        return {
            "category": "Investments",
            "remark": remark,
            "transaction_type": "UPI",
            "subcategory": "AutoPay SIP",
            "amount_direction": "debit",
            "entities": {
                "merchant": "",
                "organization": organization,
                "upi_id": upi_id,
            },
            "metadata": {
                "reference_number": reference_number,
                "date": "",
                "time": "",
                "location": "",
            },
            "explanation": "Automatic debit for mutual fund SIP via UPI AutoPay",
        }

    # POS transaction pattern
    pos_regex = re.compile(
        r"^POS\s+(?P<card>[A-Z0-9X]+)\s+(?P<txn_id>\d+)\s+(?P<date>\d{2}[A-Z]{3}\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<location>[A-Z\s]+?)\s+(?P<merchant>.+)$",
        flags=re.IGNORECASE,
    )
    pos_match = pos_regex.search(text)
    if pos_match:
        merchant = pos_match.group("merchant").strip().title()
        location = pos_match.group("location").strip().title()
        txn_id = pos_match.group("txn_id").strip()

        return {
            "category": "Shopping",
            "remark": "Card Payment at POS Merchant",
            "transaction_type": "POS",
            "subcategory": "Card Payment",
            "amount_direction": "debit",
            "entities": {
                "merchant": merchant,
                "organization": "",
                "upi_id": "",
            },
            "metadata": {
                "reference_number": txn_id,
                "date": pos_match.group("date"),
                "time": pos_match.group("time"),
                "location": location,
            },
            "explanation": "Payment made at merchant using card at POS machine",
        }

    return None


def apply_pattern_enrichment(df, description_col="description"):
    """Apply deterministic parser to dataframe and populate structured fields."""
    if description_col not in df.columns:
        return df

    out_df = df.copy()
    structured_defaults = {
        "transaction_type": "",
        "subcategory": "",
        "amount_direction": "",
        "entities": {},
        "metadata": {},
        "explanation": "",
    }

    for col, default_val in structured_defaults.items():
        if col not in out_df.columns:
            out_df[col] = default_val

    for idx, row in out_df.iterrows():
        desc = row.get(description_col, "")
        parsed = parse_rule_based_pattern(desc)
        if parsed:
            # Pattern rules are high-confidence and should apply regardless of AI provider.
            out_df.at[idx, "category"] = parsed.get("category", row.get("category", "Shopping"))
            out_df.at[idx, "remark"] = parsed.get("remark", row.get("remark", "General Purchase / Transaction"))
            out_df.at[idx, "transaction_type"] = parsed.get("transaction_type", "")
            out_df.at[idx, "subcategory"] = parsed.get("subcategory", "")
            out_df.at[idx, "amount_direction"] = parsed.get("amount_direction", "")
            out_df.at[idx, "entities"] = parsed.get("entities", {})
            out_df.at[idx, "metadata"] = parsed.get("metadata", {})
            out_df.at[idx, "explanation"] = parsed.get("explanation", "")

    return out_df
