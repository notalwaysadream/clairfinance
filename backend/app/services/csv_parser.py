import csv
import io
import re
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd

COLUMN_ALIASES = {
    "date": ["date", "transaction date", "txn date", "value date", "trans date", "booking date"],
    "description": ["description", "narration", "particulars", "remarks", "details", "transaction remarks", "merchant"],
    "amount": ["amount", "transaction amount", "txn amount", "net amount"],
    "debit": ["debit", "withdrawal", "dr", "debit amount", "withdrawals"],
    "credit": ["credit", "deposit", "cr", "credit amount", "deposits"],
    "type": ["type", "dr/cr", "transaction type", "cr/dr", "txn type"],
    "mode": ["mode", "payment mode", "channel", "method", "txn mode"],
}

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
]

def parse_date_robust(date_str: str) -> Optional[date]:
    clean_str = str(date_str).strip()
    # Strip any time component
    clean_str = re.split(r"[T\s]", clean_str)[0]
    
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue
            
    # Try pandas parser as fallback
    try:
        ts = pd.to_datetime(date_str, dayfirst=True)
        return ts.date()
    except Exception:
        return None

def clean_amount(val: Any) -> float:
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).strip().replace(",", "").replace("₹", "").replace("$", "")
    try:
        return abs(float(val_str))
    except ValueError:
        return 0.0

def detect_column_mapping(columns: List[str]) -> Dict[str, str]:
    mapping = {}
    normalized_cols = {col: re.sub(r"[_\s]+", " ", col.strip().lower()) for col in columns}
    
    for standard_name, aliases in COLUMN_ALIASES.items():
        for orig_col, norm_col in normalized_cols.items():
            if norm_col in aliases:
                mapping[standard_name] = orig_col
                break
                
    return mapping

def detect_payment_mode(description: str) -> str:
    desc = str(description).upper()
    if "UPI" in desc or "@" in desc:
        return "UPI"
    elif "NEFT" in desc:
        return "NEFT"
    elif "IMPS" in desc or "RTGS" in desc:
        return "IMPS"
    elif "POS" in desc or "CARD" in desc or "VISA" in desc or "MASTERCARD" in desc:
        return "Card"
    elif "EMI" in desc or "LOAN" in desc:
        return "EMI"
    elif "AUTO-DEBIT" in desc or "ACH" in desc or "NACH" in desc:
        return "Auto-Debit"
    elif "ATM" in desc or "CASH" in desc:
        return "Cash"
    return "UPI"

def parse_csv_content(content_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses CSV content bytes into structured transaction dictionaries.
    Handles various Indian bank formats (HDFC, SBI, ICICI, etc.)
    """
    errors = []
    transactions = []
    
    # Try multiple decodings
    text = None
    for encoding in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            text = content_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
            
    if not text:
        return [], ["Failed to decode file. Supported encodings: UTF-8, Latin-1."]

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [], ["The uploaded CSV file is empty."]

    # Find the header row (skip preamble metadata lines)
    header_idx = -1
    for idx, line in enumerate(lines[:15]):
        line_lower = line.lower()
        if ("date" in line_lower and ("description" in line_lower or "narration" in line_lower or "particulars" in line_lower or "amount" in line_lower)):
            header_idx = idx
            break

    if header_idx == -1:
        # Default to first non-empty line
        header_idx = 0

    csv_data = "\n".join(lines[header_idx:])
    
    try:
        df = pd.read_csv(io.StringIO(csv_data))
    except Exception as e:
        return [], [f"Failed to parse CSV format: {str(e)}"]

    col_map = detect_column_mapping(df.columns.tolist())
    
    # Verify mandatory fields
    if "date" not in col_map:
        return [], ["Required column 'Date' (or 'Txn Date') was not found in the CSV."]
    if "description" not in col_map:
        return [], ["Required column 'Description' (or 'Narration'/'Particulars') was not found in the CSV."]
        
    has_amount = "amount" in col_map
    has_debit_credit = "debit" in col_map or "credit" in col_map
    
    if not has_amount and not has_debit_credit:
        return [], ["Could not identify amount columns ('Amount' or 'Debit'/'Credit')."]

    for row_idx, row in df.iterrows():
        try:
            raw_date = row[col_map["date"]]
            if pd.isna(raw_date):
                continue
            parsed_date = parse_date_robust(str(raw_date))
            if not parsed_date:
                errors.append(f"Row {row_idx + 1}: Invalid date '{raw_date}'")
                continue

            raw_desc = str(row[col_map["description"]]).strip()
            if not raw_desc or raw_desc.lower() == "nan":
                continue

            txn_type = "debit"
            amount = 0.0

            if has_debit_credit:
                debit_val = clean_amount(row.get(col_map.get("debit"))) if "debit" in col_map else 0.0
                credit_val = clean_amount(row.get(col_map.get("credit"))) if "credit" in col_map else 0.0
                
                if credit_val > 0 and debit_val == 0:
                    txn_type = "credit"
                    amount = credit_val
                elif debit_val > 0:
                    txn_type = "debit"
                    amount = debit_val
                elif "amount" in col_map:
                    raw_amt = row[col_map["amount"]]
                    amount = clean_amount(raw_amt)
                    if "type" in col_map:
                        t_str = str(row[col_map["type"]]).strip().lower()
                        txn_type = "credit" if "cr" in t_str or "credit" in t_str else "debit"
            else:
                raw_amt = row[col_map["amount"]]
                if pd.isna(raw_amt):
                    continue
                # Handle negative amounts
                amt_str = str(raw_amt).strip()
                if amt_str.startswith("-") or "(" in amt_str:
                    txn_type = "debit"
                    amount = clean_amount(amt_str)
                else:
                    amount = clean_amount(amt_str)
                    if "type" in col_map:
                        t_str = str(row[col_map["type"]]).strip().lower()
                        txn_type = "credit" if ("cr" in t_str or "credit" in t_str) else "debit"
                    else:
                        # Default heuristics: if salary/credit keywords
                        desc_up = raw_desc.upper()
                        if any(w in desc_up for w in ["SALARY", "CREDIT", "REFUND", "CASHBACK", "DIVIDEND"]):
                            txn_type = "credit"
                        else:
                            txn_type = "debit"

            if amount <= 0:
                continue

            payment_mode = "UPI"
            if "mode" in col_map and not pd.isna(row[col_map["mode"]]):
                payment_mode = str(row[col_map["mode"]]).strip()
            else:
                payment_mode = detect_payment_mode(raw_desc)

            transactions.append({
                "date": parsed_date,
                "description": raw_desc,
                "amount": round(amount, 2),
                "type": txn_type,
                "payment_mode": payment_mode,
                "raw_description": raw_desc,
            })
        except Exception as ex:
            errors.append(f"Row {row_idx + 1}: {str(ex)}")

    return transactions, errors
