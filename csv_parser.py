from pathlib import Path
import pandas as pd
import re

def read_csv(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)
    df = pd.read_csv(
        path,
        encoding='utf-8-sig',
        sep=None,
        engine='python',
        dtype=str, #handling parsing later, subject to change
        keep_default_na=False
    )
    return df
    
    
def find_column(df, names):
    cols = {col.strip().lower(): col for col in df.columns}
    for name in names:
        key=name.strip().lower()
        if key in cols:
            return cols[key]
    return None


def build_column_mapping(df):
    cols = {
        'date': find_column(df, ['Date']),
        'amount': find_column(df, ['Net']), 
        'external_id': find_column(df, ['Transaction ID']),
        'status': find_column(df, ['Status']),
        'name': find_column(df, ['Name']),
        'item_title': find_column(df, ['Item Title']),
        'subject': find_column(df, ['Subject']),
        'note': find_column(df, ['Note']),
    }
    missing = [k for k in ('date', 'amount', 'external_id') if not cols[k]] #should external id be mandatory?
    if missing:
        raise ValueError(f'Missing required columns: {missing}')
    return cols


def parse_date(date_str: str):
    date_str = (date_str or '').strip()
    if not date_str:
        raise ValueError('date missing')
    dt = pd.to_datetime(date_str, dayfirst=True, errors='raise')
    return dt.date().isoformat()


def parse_amount(amount_str: str) -> float:
    amount_str = (amount_str or '').strip()
    if not amount_str:
        raise ValueError('empty amount')
    
    amount_str = re.sub(r'[^\d\-,\.]', '', amount_str)
    
    #assumption: last dot/comma is for decimal 
    last_dot = amount_str.rfind('.')
    last_comma = amount_str.rfind(',')
    sep_pos = max(last_dot, last_comma)
    
    if sep_pos != -1:
        integer_part = re.sub(r'[^\d\-]', '', amount_str[:sep_pos])
        decimal_part = re.sub(r'[^\d]', '', amount_str[sep_pos + 1:])
        normalized = f'{integer_part}.{decimal_part}'
    else:
        normalized = re.sub(r'[^\d\-]', '', amount_str)

    return float(normalized)


def pick_description(row: dict, cols: dict[str, str | None]) -> str:
    for key in ('item_title', 'subject', 'note'):
        col = cols.get(key)
        if not col:
            continue
        
        value = (row.get(col) or '').strip()
        if value:
            return value
    return ''


#main parsing function: 
def parse_transactions_from_csv(
    csv_path: str | Path,
    source: str = 'paypal',
    default_category: str = 'Uncategorized',
    only_completed: bool = True,
    ) -> list[dict]:
    
    df = read_csv(csv_path)
    cols = build_column_mapping(df)

    transactions: list[dict] = []

    for row in df.to_dict(orient='records'):
        external_id = (row.get(cols['external_id']) or '').strip()
        if not external_id: #in this case no duplicate check possible, maybe should adjust rest of code to keep optional 
            continue  
        if only_completed and cols['status']:
            status = (row.get(cols['status']) or '').strip().lower()
            if status and status != 'completed':
                continue

        tx_date = parse_date(row.get(cols['date']) or '')
        amount = parse_amount(row.get(cols['amount']) or '')

        name = (row.get(cols['name']) or '').strip() if cols['name'] else ''
        description = pick_description(row, cols)

        transactions.append({
            'tx_date': tx_date,
            'amount': amount,
            'name': name or None,
            'description': description or None,
            'category': default_category,
            'source': source,
            'external_id': external_id,
        })
        
    return transactions
