import re
import pandas as pd


INDIA_TRANSACTION_MODES = [
    "UPI",
    "IMPS",
    "NEFT",
    "RTGS",
    "NACH_AUTODEBIT",
    "CARD_POS",
    "CARD_ECOM",
    "ATM",
    "CASH",
    "CHEQUE",
    "BANK_INTERNAL",
    "SALARY",
    "INTEREST",
    "CHARGES",
    "INVESTMENT",
    "BILL_PAYMENT",
    "SUBSCRIPTION",
    "INTERNATIONAL",
]


def _contains_any(text, keywords):
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def detect_transaction_mode_with_confidence(description, row=None):
    """Detect transaction mode and confidence (High/Medium/Low)."""
    text = str(description or "").strip()
    low = text.lower()

    tx_type = ""
    subcategory = ""
    if row is not None:
        tx_type = str(row.get("transaction_type", "") or "").lower()
        subcategory = str(row.get("subcategory", "") or "").lower()

    # High confidence: explicit rails/tokens in statement narration.
    if _contains_any(low, ["imps"]):
        return "IMPS", "High"
    if _contains_any(low, ["neft"]):
        return "NEFT", "High"
    if _contains_any(low, ["rtgs"]):
        return "RTGS", "High"

    if _contains_any(low, ["upi", "@ok", "@ybl", "@ibl", "@axl", "@hdfcbank", "@paytm"]):
        if _contains_any(low, ["mfautopay", "nach", "ecs", "autodebit", "auto debit", "sip"]) or "autopay" in subcategory:
            return "NACH_AUTODEBIT", "High"
        return "UPI", "High"

    if low.startswith("pos") or _contains_any(low, [" pos ", "swipe", "tap", "contactless"]):
        return "CARD_POS", "High"
    if _contains_any(low, ["ecom", "online card", "card not present", "pg", "gateway", "eci", "3d secure"]):
        return "CARD_ECOM", "High"

    if _contains_any(low, ["atm wdl", "atm withdrawal", "atm dep", "atm deposit", "atm"]):
        return "ATM", "High"
    if _contains_any(low, ["cash deposit", "cash withdrawal", "cash wdl", "cash"]):
        return "CASH", "High"
    if _contains_any(low, ["cheque", "chq", "cts clearing", "chq return", "cheque return", "cheque bounce"]):
        return "CHEQUE", "High"

    if _contains_any(low, ["salary", "payroll", "salary credit"]):
        return "SALARY", "High"
    if _contains_any(low, ["interest credit", "int.pd", "interest"]):
        return "INTEREST", "High"
    if _contains_any(low, ["charges", "charge", "fee", "gst on charges", "annual fee", "penalty"]):
        return "CHARGES", "High"

    if _contains_any(low, ["mutual fund", "sip", "demat", "dividend", "insurance premium", "nps", "pension"]):
        return "INVESTMENT", "High"
    if _contains_any(low, ["bill pay", "bbps", "electricity", "water bill", "gas bill", "recharge", "dth"]):
        return "BILL_PAYMENT", "High"
    if _contains_any(low, ["subscription", "netflix", "spotify", "prime", "youtube", "ott", "apple.com/bill"]):
        return "SUBSCRIPTION", "High"
    if _contains_any(low, ["swift", "forex", "international", "cross border", "visa intl", "mc intl"]):
        return "INTERNATIONAL", "High"

    # Medium confidence: inferred from structured enrichment hints.
    if tx_type == "upi":
        if "autopay" in subcategory:
            return "NACH_AUTODEBIT", "Medium"
        return "UPI", "Medium"
    if tx_type == "pos":
        return "CARD_POS", "Medium"
    if "autopay sip" in subcategory:
        return "INVESTMENT", "Medium"
    if _contains_any(low, ["self transfer", "transfer within bank", "internal transfer", "sweep in", "sweep out", "auto sweep"]):
        return "BANK_INTERNAL", "Medium"
    if _contains_any(low, ["transfer", "trf", "txn", "bank transfer"]):
        return "BANK_INTERNAL", "Medium"

    # Low confidence: fallback mapping when statement tokens are unclear.
    return "BANK_INTERNAL", "Low"


def detect_transaction_mode(description, row=None):
    """Detect transaction mode using statement text and available structured hints."""
    mode, _ = detect_transaction_mode_with_confidence(description, row)
    return mode


def apply_transaction_modes(df, description_col="description"):
    """Populate transaction_mode column using the allowed India transaction modes only."""
    if description_col not in df.columns:
        return df

    out_df = df.copy()
    detected = out_df.apply(
        lambda row: detect_transaction_mode_with_confidence(row.get(description_col, ""), row),
        axis=1,
    )
    out_df["transaction_mode"] = detected.apply(lambda x: x[0])
    out_df["mode_confidence"] = detected.apply(lambda x: x[1])

    out_df["transaction_mode"] = out_df["transaction_mode"].where(
        out_df["transaction_mode"].isin(INDIA_TRANSACTION_MODES),
        "BANK_INTERNAL",
    )

    return out_df


def summarize_modes(df, amount_col="debit"):
    """Return mode summary with count and amount for quick dashboard display."""
    if "transaction_mode" not in df.columns:
        return pd.DataFrame(columns=["transaction_mode", "count", "amount"])

    tmp = df.copy()
    tmp[amount_col] = pd.to_numeric(tmp.get(amount_col), errors="coerce").fillna(0)

    summary = (
        tmp.groupby("transaction_mode", as_index=False)
        .agg(count=("transaction_mode", "count"), amount=(amount_col, "sum"))
        .sort_values(["amount", "count"], ascending=[False, False])
    )
    return summary
