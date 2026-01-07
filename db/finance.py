import sqlite3
from datetime import date as dt_date, date, datetime
from helpers.dates import valid_day

#on the transactions table: 
#amount is stored in JPY
#optional data if transaction was originally in other currency:
#currency: original currency code
#amount_original: amount in original currency
#fx_rate_to_jpy: rate used to convert amount_original to amount in JPY

def init_finance_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            amount REAL NOT NULL,

            currency TEXT NOT NULL DEFAULT 'JPY',
            amount_original REAL,
            fx_rate_to_jpy REAL,

            name TEXT,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'Uncategorized',
            source TEXT,
            recurring_rule_id INTEGER,
            external_id TEXT UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS index_tx_date ON transactions(tx_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS index_tx_rr ON transactions(recurring_rule_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS index_tx_source ON transactions(source)")
    connection.execute("CREATE INDEX IF NOT EXISTS index_tx_category ON transactions(category)")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recurring_rules(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,

            amount REAL NOT NULL,

            currency TEXT NOT NULL DEFAULT 'JPY',
            amount_original REAL,
            fx_rate_to_jpy REAL,

            category TEXT NOT NULL DEFAULT 'Uncategorized',
            description TEXT,
            day_of_month INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS index_rr_active ON recurring_rules(active)")
    connection.execute("CREATE INDEX IF NOT EXISTS index_rr_start ON recurring_rules(start_date)")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS currency_rates(
            currency TEXT PRIMARY KEY,
            fx_rate_to_jpy REAL NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    # some basic defaults, maybe get via some API call later 
    connection.execute(
        "INSERT OR IGNORE INTO currency_rates (currency, fx_rate_to_jpy) VALUES (?, ?)",
        ("USD", 155.0),
    )
    connection.execute(
        "INSERT OR IGNORE INTO currency_rates (currency, fx_rate_to_jpy) VALUES (?, ?)",
        ("EUR", 165.0),
    )
    connection.execute(
        "INSERT OR IGNORE INTO currency_rates (currency, fx_rate_to_jpy) VALUES (?, ?)",
        ("GBP", 195.0),
    )

    connection.commit()


#currency rates

def normalize_currency(value: str | None) -> str:
    v = (value or "JPY").strip().upper()
    return v if v else "JPY"


def get_fx_rate_to_jpy(connection: sqlite3.Connection, currency: str) -> float | None:
    cur = normalize_currency(currency)
    if cur == "JPY":
        return 1.0

    row = connection.execute(
        "SELECT fx_rate_to_jpy FROM currency_rates WHERE currency = ?",
        (cur,),
    ).fetchone()

    if not row:
        return None
    return float(row["fx_rate_to_jpy"])


def set_fx_rate_to_jpy(connection: sqlite3.Connection, currency: str, fx_rate_to_jpy: float) -> None:
    cur = normalize_currency(currency)
    if cur == "JPY":
        return

    if fx_rate_to_jpy is None or float(fx_rate_to_jpy) <= 0:
        raise ValueError("fx_rate_to_jpy must be > 0")

    connection.execute(
        """
        INSERT INTO currency_rates (currency, fx_rate_to_jpy, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(currency) DO UPDATE SET
            fx_rate_to_jpy = excluded.fx_rate_to_jpy,
            updated_at = datetime('now')
        """,
        (cur, float(fx_rate_to_jpy)),
    )
    connection.commit()


def convert_to_jpy(
    connection: sqlite3.Connection,
    currency: str | None,
    amount_original: float | None,
    fx_rate_to_jpy: float | None,
    fallback_amount_jpy: float | None,
) -> tuple[float, str, float | None, float | None]:
    cur = normalize_currency(currency)

    if cur == "JPY":
        amt_jpy = float(fallback_amount_jpy or amount_original or 0.0)
        return amt_jpy, "JPY", None, None

    if amount_original is None:
        raise ValueError("amount_original required for non-JPY transaction")

    fx = float(fx_rate_to_jpy) if fx_rate_to_jpy is not None else None
    if fx is None:
        fx = get_fx_rate_to_jpy(connection, cur)

    if fx is None or float(fx) <= 0:
        raise ValueError(f"missing fx_rate_to_jpy for currency: {cur}")

    amt_jpy = float(round(float(amount_original) * float(fx)))
    return amt_jpy, cur, float(amount_original), float(fx)

# transactions

def insert_transaction(
    connection: sqlite3.Connection,
    tx_date: str,
    amount: float,
    name: str | None = None,
    description: str | None = None,
    category: str = "Uncategorized",
    source: str | None = None,
    external_id: str | None = None,
    recurring_rule_id: int | None = None,
    currency: str | None = "JPY",
    amount_original: float | None = None,
    fx_rate_to_jpy: float | None = None,
) -> int | None:
    amt_jpy, cur, amt_orig, fx = convert_to_jpy(
        connection=connection,
        currency=currency,
        amount_original=amount_original,
        fx_rate_to_jpy=fx_rate_to_jpy,
        fallback_amount_jpy=amount,
    )

    cur2 = connection.execute(
        """
        INSERT OR IGNORE INTO transactions
        (tx_date, amount, currency, amount_original, fx_rate_to_jpy,
         name, description, category, source, recurring_rule_id, external_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tx_date,
            amt_jpy,
            cur,
            amt_orig,
            fx,
            name,
            description,
            category,
            source,
            recurring_rule_id,
            external_id,
        ),
    )
    connection.commit()
    return cur2.lastrowid if cur2.rowcount else None


def delete_transaction(connection: sqlite3.Connection, tx_id: int) -> None:
    connection.execute("DELETE FROM transactions WHERE id = ?", (int(tx_id),))
    connection.commit()


def update_transaction(
    connection: sqlite3.Connection,
    tx_id: int,
    tx_date: str,
    amount: float,
    category: str,
    name: str | None = None,
    description: str | None = None,
    currency: str | None = "JPY",
    amount_original: float | None = None,
    fx_rate_to_jpy: float | None = None,
) -> None:
    amt_jpy, cur, amt_orig, fx = convert_to_jpy(
        connection=connection,
        currency=currency,
        amount_original=amount_original,
        fx_rate_to_jpy=fx_rate_to_jpy,
        fallback_amount_jpy=amount,
    )

    connection.execute(
        """
        UPDATE transactions
        SET tx_date = ?,
            amount = ?,
            currency = ?,
            amount_original = ?,
            fx_rate_to_jpy = ?,
            category = ?,
            name = ?,
            description = ?
        WHERE id = ?
        """,
        (tx_date, amt_jpy, cur, amt_orig, fx, category, name, description, int(tx_id)),
    )
    connection.commit()


# deprecated
def update_transaction_category(connection: sqlite3.Connection, tx_id: int, category: str) -> None:
    connection.execute("UPDATE transactions SET category = ? WHERE id = ?", (category, int(tx_id)))
    connection.commit()


def get_transaction_by_id(connection: sqlite3.Connection, tx_id: int) -> dict | None:
    q = connection.execute(
        """
        SELECT
            id, tx_date, amount,
            currency, amount_original, fx_rate_to_jpy,
            category, name, description, source, recurring_rule_id, external_id
        FROM transactions
        WHERE id = ?
        """,
        (int(tx_id),),
    )
    row = q.fetchone()
    return dict(row) if row else None


def list_transactions(
    connection: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    tx_type: str = "All",
    category: str | None = None,
    limit: int = 200,
    exclude_recurring: bool = False,
) -> list[dict]:
    where = []
    params: list = []

    if start_date and end_date:
        where.append("tx_date BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    if tx_type == "Expenses":
        where.append("amount < 0")
    elif tx_type == "Income":
        where.append("amount > 0")

    if category and category != "All":
        where.append("category = ?")
        params.append(category)

    if exclude_recurring:
        where.append("(source IS NULL OR source != 'recurring')")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    cur = connection.execute(
        f"""
        SELECT
            id,
            tx_date as date,
            amount,
            COALESCE(NULLIF(category, ''), 'Uncategorized') as category,
            COALESCE(name, '') as name,
            COALESCE(description, '') as info,
            COALESCE(source, '') as source,
            recurring_rule_id,
            currency,
            amount_original,
            fx_rate_to_jpy
        FROM transactions
        {where_sql}
        ORDER BY tx_date DESC, id DESC
        LIMIT ?
        """,
        (*params, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def get_categories(connection: sqlite3.Connection) -> list[str]:
    q = connection.execute(
        """
        SELECT DISTINCT COALESCE(NULLIF(category, ''), 'Uncategorized') AS category
        FROM transactions
        ORDER BY category COLLATE NOCASE
        """
    )
    return [row["category"] for row in q.fetchall()]


def get_all_transactions(connection: sqlite3.Connection):
    q = connection.execute("SELECT id, tx_date, amount FROM transactions")
    return q.fetchall()


def import_transactions(connection: sqlite3.Connection, transactions: list[dict]) -> dict[str, int]:
    stats = {"imported": 0, "duplicates": 0, "failed": 0}

    for tx in transactions:
        try:
            inserted_id = insert_transaction(
                connection=connection,
                tx_date=tx["tx_date"],
                amount=float(tx.get("amount") or 0.0),
                name=tx.get("name"),
                description=tx.get("description"),
                category=tx.get("category", "Uncategorized"),
                source=tx.get("source"),
                external_id=tx.get("external_id"),
                recurring_rule_id=tx.get("recurring_rule_id"),
                currency=tx.get("currency", "JPY"),
                amount_original=tx.get("amount_original"),
                fx_rate_to_jpy=tx.get("fx_rate_to_jpy"),
            )
        except Exception:
            stats["failed"] += 1
            continue

        if inserted_id is None:
            stats["duplicates"] += 1
        else:
            stats["imported"] += 1

    return stats

#for finance analytics stuff 
def get_timeseries_data(
    connection: sqlite3.Connection,
    start_date: str,
    end_date: str,
    aggregation: str,
    exclude_recurring: bool = False,
) -> list[dict]:

    if aggregation == "day":
        label = "tx_date"
    elif aggregation == "week":
        label = "date(tx_date, '-' || ((CAST(strftime('%w', tx_date) AS integer) + 6) % 7) || ' days')"
    elif aggregation == "month":
        label = "date(tx_date, 'start of month')"
    elif aggregation == "year":
        label = "date(tx_date, 'start of year')"
    else:
        raise ValueError(f"Invalid aggregation: {aggregation}")

    extra = ""
    if exclude_recurring:
        extra = " AND (source IS NULL OR source != 'recurring')"

    cur = connection.execute(
        f"""
        SELECT {label} as label,
               SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as expenses
        FROM transactions
        WHERE tx_date BETWEEN ? AND ? {extra}
        GROUP BY label
        ORDER BY label ASC
        """,
        (start_date, end_date),
    )

    result: list[dict] = []
    for label_value, income, expenses in cur.fetchall():
        result.append(
            {
                "label": label_value,
                "income": float(income or 0),
                "expenses": float(expenses or 0),
            }
        )
    return result


def list_recent_transactions(connection: sqlite3.Connection, limit: int = 10) -> list[dict]:
    q = connection.execute(
        """
        SELECT
            id,
            tx_date AS date,
            amount,
            COALESCE(NULLIF(category, ''), 'Uncategorized') AS category,
            COALESCE(name, '') AS name,
            COALESCE(description, '') AS description,
            COALESCE(source, '') AS source,
            recurring_rule_id,
            currency,
            amount_original,
            fx_rate_to_jpy
        FROM transactions
        ORDER BY tx_date DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in q.fetchall()]


def get_mtd_summary(connection: sqlite3.Connection, day_iso: str) -> dict:
    day = dt_date.fromisoformat(day_iso)
    start = dt_date(day.year, day.month, 1).isoformat()

    q = connection.execute(
        """
        SELECT
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS income,
            SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) AS expenses
        FROM transactions
        WHERE tx_date >= ?
          AND tx_date <= ?
        """,
        (start, day_iso),
    )
    row = q.fetchone()
    income = float(row["income"] or 0)
    expenses = float(row["expenses"] or 0)
    net = income + expenses

    return {
        "income": income,
        "expenses": expenses,
        "net": net,
        "start_date": start,
        "end_date": day_iso,
    }


# recurring transaction rules

def create_recurring_rule(
    connection: sqlite3.Connection,
    name: str,
    amount: float,
    category: str,
    description: str | None,
    day_of_month: int,
    start_date: str,
    currency: str | None = "JPY",
    amount_original: float | None = None,
    fx_rate_to_jpy: float | None = None,
) -> int:
    amt_jpy, cur, amt_orig, fx = convert_to_jpy(
        connection=connection,
        currency=currency,
        amount_original=amount_original,
        fx_rate_to_jpy=fx_rate_to_jpy,
        fallback_amount_jpy=amount,
    )

    cur2 = connection.execute(
        """
        INSERT INTO recurring_rules
        (name, amount, currency, amount_original, fx_rate_to_jpy,
         category, description, day_of_month, start_date, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            name,
            float(amt_jpy),
            cur,
            amt_orig,
            fx,
            category,
            description,
            int(day_of_month),
            start_date,
        ),
    )
    connection.commit()
    return int(cur2.lastrowid)


def stop_recurring_rule(connection: sqlite3.Connection, rule_id: int, end_date: str | None = None) -> None:
    if end_date is None:
        end_date = date.today().isoformat()

    connection.execute(
        """
        UPDATE recurring_rules
        SET active = 0, end_date = ?
        WHERE id = ?
        """,
        (end_date, int(rule_id)),
    )
    connection.commit()


def list_recurring_rules(connection: sqlite3.Connection, active_only: bool = False) -> list[dict]:
    if active_only:
        q = connection.execute(
            """
            SELECT
                id, name, amount, currency, amount_original, fx_rate_to_jpy,
                category, description, day_of_month, start_date, end_date, active
            FROM recurring_rules
            WHERE active = 1
            ORDER BY id DESC
            """
        )
    else:
        q = connection.execute(
            """
            SELECT
                id, name, amount, currency, amount_original, fx_rate_to_jpy,
                category, description, day_of_month, start_date, end_date, active
            FROM recurring_rules
            ORDER BY active DESC, id DESC
            """
        )
    return [dict(r) for r in q.fetchall()]


def get_recurring_rule_by_id(connection: sqlite3.Connection, rule_id: int) -> dict | None:
    q = connection.execute(
        """
        SELECT
            id, name, amount, currency, amount_original, fx_rate_to_jpy,
            category, description, day_of_month, start_date, end_date, active
        FROM recurring_rules
        WHERE id = ?
        """,
        (int(rule_id),),
    )
    row = q.fetchone()
    return dict(row) if row else None


def update_recurring_rule(
    connection: sqlite3.Connection,
    rule_id: int,
    name: str,
    amount: float,
    category: str,
    description: str | None,
    day_of_month: int,
    start_date: str,
    active: bool,
    end_date: str | None,
    currency: str | None = "JPY",
    amount_original: float | None = None,
    fx_rate_to_jpy: float | None = None,
) -> None:
    amt_jpy, cur, amt_orig, fx = convert_to_jpy(
        connection=connection,
        currency=currency,
        amount_original=amount_original,
        fx_rate_to_jpy=fx_rate_to_jpy,
        fallback_amount_jpy=amount,
    )

    connection.execute(
        """
        UPDATE recurring_rules
        SET name = ?,
            amount = ?,
            currency = ?,
            amount_original = ?,
            fx_rate_to_jpy = ?,
            category = ?,
            description = ?,
            day_of_month = ?,
            start_date = ?,
            active = ?,
            end_date = ?
        WHERE id = ?
        """,
        (
            name,
            float(amt_jpy),
            cur,
            amt_orig,
            fx,
            category,
            description,
            int(day_of_month),
            start_date,
            1 if active else 0,
            end_date,
            int(rule_id),
        ),
    )
    connection.commit()


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def add_months(value: date, months: int) -> date:
    y = value.year + (value.month - 1 + months) // 12
    m = (value.month - 1 + months) % 12 + 1
    return date(y, m, 1)

def sync_recurring_transactions(
    connection: sqlite3.Connection,
    rule_id: int | None = None,
    up_to_date: str | None = None,
) -> dict[str, int]:
    if up_to_date is None:
        up_to = date.today()
    else:
        up_to = parse_iso_date(up_to_date)

    if rule_id is None:
        rules = list_recurring_rules(connection, active_only=False)
    else:
        r = get_recurring_rule_by_id(connection, int(rule_id))
        rules = [r] if r else []

    inserted = 0
    duplicates = 0

    with connection:
        for r in rules:
            rid = int(r["id"])
            start = parse_iso_date(r["start_date"])
            end = parse_iso_date(r["end_date"]) if r.get("end_date") else up_to

            if end < start:
                continue

            m = month_start(start)
            last_m = month_start(end)

            while m <= last_m:
                tx_dt = valid_day(m.year, m.month, int(r["day_of_month"]))
                if tx_dt < start or tx_dt > end:
                    m = add_months(m, 1)
                    continue

                ext = f"rr:{rid}:{tx_dt.strftime('%Y-%m')}"
                cur2 = connection.execute(
                    """
                    INSERT OR IGNORE INTO transactions
                    (tx_date, amount, currency, amount_original, fx_rate_to_jpy,
                     name, description, category, source, recurring_rule_id, external_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'recurring', ?, ?)
                    """,
                    (
                        tx_dt.isoformat(),
                        float(r["amount"]), 
                        normalize_currency(r.get("currency")),
                        r.get("amount_original"),
                        r.get("fx_rate_to_jpy"),
                        r["name"],
                        r.get("description") or "",
                        r.get("category") or "Uncategorized",
                        rid,
                        ext,
                    ),
                )

                if cur2.rowcount == 1:
                    inserted += 1
                else:
                    duplicates += 1

                m = add_months(m, 1)

    return {"inserted": inserted, "duplicates": duplicates}


def list_currencies(connection: sqlite3.Connection) -> list[str]:
    q = connection.execute(
        "SELECT currency FROM currency_rates ORDER BY currency"
    )
    return [row["currency"] for row in q.fetchall()]

#helper functions for achievements
def has_spendthrift_transaction(connection: sqlite3.Connection, threshold_jpy: int = 1_000_000) -> bool:
    cur = connection.execute(
        """
        SELECT 1
        FROM transactions
        WHERE amount <= ?
        LIMIT 1
        """,
        (-int(threshold_jpy),),
    )
    return cur.fetchone() is not None


def has_breadwinner_transaction(connection: sqlite3.Connection, threshold_jpy: int = 1_000_000) -> bool:
    cur = connection.execute(
        """
        SELECT 1
        FROM transactions
        WHERE amount >= ?
        LIMIT 1
        """,
        (int(threshold_jpy),),
    )
    return cur.fetchone() is not None
