import json
from pathlib import Path
import re
from difflib import SequenceMatcher


MAPPING_FILE_PATH = Path(__file__).parent / "user_mappings.json"


def load_user_mappings():
    """Load user narration mappings from disk."""
    if not MAPPING_FILE_PATH.exists():
        return []

    try:
        with open(MAPPING_FILE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
    except Exception:
        return []

    return []


def save_user_mapping(pattern, category, remark, match_type="contains"):
    """Add or update a user mapping and persist to disk."""
    pattern = str(pattern or "").strip()
    category = str(category or "").strip()
    remark = str(remark or "").strip()
    match_type = str(match_type or "contains").strip().lower()

    if not pattern:
        raise ValueError("Pattern cannot be empty.")
    if not category:
        raise ValueError("Category cannot be empty.")
    if not remark:
        raise ValueError("Remark cannot be empty.")
    if match_type not in {"contains", "exact", "similar"}:
        raise ValueError("match_type must be 'contains', 'exact', or 'similar'.")

    mappings = load_user_mappings()

    updated = False
    for item in mappings:
        if item.get("pattern", "").lower() == pattern.lower() and item.get("match_type", "contains") == match_type:
            item["category"] = category
            item["remark"] = remark
            updated = True
            break

    if not updated:
        mappings.append(
            {
                "pattern": pattern,
                "match_type": match_type,
                "category": category,
                "remark": remark,
            }
        )

    with open(MAPPING_FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(mappings, file, ensure_ascii=False, indent=2)


def find_mapping_for_description(description, mappings=None):
    """Find the first matching user rule for a narration/description."""
    text = str(description or "").strip()
    if not text:
        return None

    if mappings is None:
        mappings = load_user_mappings()

    text_lower = text.lower()

    # Exact rules first, then contains, then similar.
    for preferred_type in ["exact", "contains", "similar"]:
        for item in mappings:
            pattern = str(item.get("pattern", "")).strip()
            if not pattern:
                continue
            if item.get("match_type", "contains") != preferred_type:
                continue

            pattern_lower = pattern.lower()
            if preferred_type == "exact" and text_lower == pattern_lower:
                return item
            if preferred_type == "contains" and pattern_lower in text_lower:
                return item
            if preferred_type == "similar":
                if is_similar_narration(text, pattern):
                    return item

    return None


def apply_user_mappings_to_df(df, description_col="description"):
    """Apply saved user mappings directly on dataframe category/remark."""
    mappings = load_user_mappings()
    if not mappings or description_col not in df.columns:
        return df

    updated_df = df.copy()

    for index, row in updated_df.iterrows():
        desc = row.get(description_col, "")
        rule = find_mapping_for_description(desc, mappings)
        if rule:
            updated_df.at[index, "category"] = rule.get("category", "Shopping")
            updated_df.at[index, "remark"] = build_dynamic_remark(
                desc,
                rule.get("remark", "General Purchase / Transaction")
            )

    return updated_df


def normalize_for_similarity(text):
    """Normalize narration by removing volatile IDs and extra separators."""
    normalized = str(text or "").lower().strip()
    if not normalized:
        return ""

    # Replace common UPI handles and long numeric references with placeholders.
    normalized = re.sub(r"[a-z0-9._%+-]+@[a-z0-9.-]+", " <handle> ", normalized)
    normalized = re.sub(r"\b\d{6,}\b", " <num> ", normalized)
    normalized = re.sub(r"[\-_/]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def is_similar_narration(text, pattern):
    """Heuristic matcher for similar narrations with variable IDs/person names."""
    a = normalize_for_similarity(text)
    b = normalize_for_similarity(pattern)
    if not a or not b:
        return False

    ratio = SequenceMatcher(None, a, b).ratio()
    if ratio >= 0.68:
        return True

    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens.intersection(b_tokens)) / max(1, len(b_tokens))
    return overlap >= 0.6


def extract_upi_person_name(description):
    """Extract likely payee name from UPI narration patterns."""
    text = str(description or "")
    match = re.search(r"UPI-([^\-]+)-", text, flags=re.IGNORECASE)
    if not match:
        return None

    candidate = match.group(1).strip()
    if not candidate:
        return None

    # Remove common non-name tokens and normalize spacing/case.
    candidate = re.sub(r"\b(GPAY|PAYTM|PHONEPE|BHIM|UPI)\b", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -_")
    if not candidate:
        return None
    return candidate.title()


def build_dynamic_remark(description, base_remark):
    """Create dynamic remark for UPI-person transfers when applicable."""
    remark = str(base_remark or "").strip()
    if not remark:
        remark = "General Purchase / Transaction"

    lower_desc = str(description or "").lower()
    if "upi" in lower_desc and "payment to" in lower_desc and "upi payment to" in remark.lower():
        person = extract_upi_person_name(description)
        if person:
            return f"UPI Payment to {person}"

    return remark
