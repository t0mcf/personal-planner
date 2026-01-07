from pathlib import Path
import pandas as pd
import re


def read_csv(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        sep=None,
        engine="python",
        dtype=str,
        keep_default_na=False,
    )
    return df


def normalize_col_name(s: str) -> str:
    return (s or "").strip()


def find_column(df: pd.DataFrame, names: list[str]) -> str | None:
    cols = {col.strip().lower(): col for col in df.columns}
    for name in names:
        key = name.strip().lower()
        if key in cols:
            return cols[key]
    return None


def paypal_preset_mapping(df: pd.DataFrame) -> dict[str, str | None]:
    cols = {
        "date": find_column(df, ["Date"]),
        "amount": find_column(df, ["Net"]),
        "external_id": find_column(df, ["Transaction ID"]),
        "status": find_column(df, ["Status"]),
        "name": find_column(df, ["Name"]),
        "item_title": find_column(df, ["Item Title"]),
        "subject": find_column(df, ["Subject"]),
        "note": find_column(df, ["Note"]),
        "currency": find_column(df, ["Currency"]),
        # optional custom single-column description (paypal usually doesn't have this)
        "description": None,
        "category": None,
    }
    return cols


def build_mapping_from_user_input(df: pd.DataFrame, user_mapping: dict[str, str | None]) -> dict[str, str | None]:
    # user gives column names; we validate they exist (case-sensitive match via df.columns)
    # but allow empty/None for optional fields

    mapping: dict[str, str | None] = {}
    df_cols = set(df.columns)

    for key, col in (user_mapping or {}).items():
        c = normalize_col_name(col)
        if not c:
            mapping[key] = None
            continue
        if c not in df_cols:
            raise ValueError(f'Column not found for "{key}": "{c}"')
        mapping[key] = c

    return mapping


def validate_required(mapping: dict[str, str | None]) -> None:
    missing = [k for k in ("date", "amount", "external_id") if not mapping.get(k)]
    if missing:
        raise ValueError(f"Missing required mappings: {missing}")


def parse_date(date_str: str) -> str:
    date_str = (date_str or "").strip()
    if not date_str:
        raise ValueError("date missing")
    dt = pd.to_datetime(date_str, dayfirst=False, errors="raise")
    return dt.date().isoformat()


def parse_amount(amount_str: str) -> float:
    amount_str = (amount_str or "").strip()
    if not amount_str:
        raise ValueError("empty amount")

    amount_str = re.sub(r"[^\d\-,\.]", "", amount_str)

    last_dot = amount_str.rfind(".")
    last_comma = amount_str.rfind(",")
    sep_pos = max(last_dot, last_comma)

    if sep_pos != -1:
        integer_part = re.sub(r"[^\d\-]", "", amount_str[:sep_pos])
        decimal_part = re.sub(r"[^\d]", "", amount_str[sep_pos + 1 :])
        normalized = f"{integer_part}.{decimal_part}" if decimal_part else integer_part
    else:
        normalized = re.sub(r"[^\d\-]", "", amount_str)

    return float(normalized)


def pick_description(row: dict, mapping: dict[str, str | None]) -> str:
    # if user mapped a direct description column, use it
    desc_col = mapping.get("description")
    if desc_col:
        v = (row.get(desc_col) or "").strip()
        if v:
            return v

    # else fall back to common paypal-ish columns if present
    for key in ("item_title", "subject", "note"):
        col = mapping.get(key)
        if not col:
            continue
        value = (row.get(col) or "").strip()
        if value:
            return value

    return ""


def parse_currency(value: str | None, default_currency: str = "JPY") -> str:
    v = (value or "").strip().upper()
    return v if v else (default_currency or "JPY")


def parse_transactions_from_csv(
    csv_path: str | Path,
    source: str = "csv",
    default_category: str = "Uncategorized",
    default_currency: str = "JPY",
    only_completed: bool = False,
    mapping: dict[str, str | None] | None = None,
    preset: str | None = None,  # e.g. "paypal"
) -> list[dict]:
    df = read_csv(csv_path)

    if preset and preset.lower() == "paypal":
        cols = paypal_preset_mapping(df)
        only_completed = True if only_completed is None else only_completed
    else:
        cols = build_mapping_from_user_input(df, mapping or {})

    validate_required(cols)

    transactions: list[dict] = []

    for row in df.to_dict(orient="records"):
        external_id = (row.get(cols["external_id"]) or "").strip()
        if not external_id:
            continue

        if only_completed and cols.get("status"):
            status = (row.get(cols["status"]) or "").strip().lower()
            if status and status != "completed":
                continue

        tx_date = parse_date(row.get(cols["date"]) or "")
        amount_original = parse_amount(row.get(cols["amount"]) or "")

        name = (row.get(cols["name"]) or "").strip() if cols.get("name") else ""
        description = pick_description(row, cols)

        category = default_category
        if cols.get("category"):
            cv = (row.get(cols["category"]) or "").strip()
            if cv:
                category = cv

        currency = default_currency
        if cols.get("currency"):
            currency = parse_currency(row.get(cols["currency"]), default_currency=default_currency)
        else:
            currency = parse_currency(None, default_currency=default_currency)

        # output:
        # - for JPY we can store amount directly as fallback
        # - for non-JPY we store amount_original + currency, and db layer converts using currency_rates
        tx: dict = {
            "tx_date": tx_date,
            "name": name or None,
            "description": description or None,
            "category": category or "Uncategorized",
            "source": source,
            "external_id": external_id,
            "currency": currency,
        }

        if currency == "JPY":
            tx["amount"] = float(amount_original)
            tx["amount_original"] = None
        else:
            tx["amount"] = 0.0
            tx["amount_original"] = float(amount_original)

        transactions.append(tx)

    return transactions
