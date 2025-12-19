import sqlite3
from pathlib import Path

DB_PATH = Path('data') / 'finance.db'

def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


#scheme explanation:
#name is for merchants etc
#source is whether manual or paypal etc (subject to change)
#external_id to check for duplicate imports (subject to change)
def init_db(connection: sqlite3.Connection) -> None:
    connection.execute("""
                       CREATE TABLE IF NOT EXISTS transactions(
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           tx_date TEXT NOT NULL,
                           amount REAL NOT NULL,
                           name TEXT,
                           description TEXT,
                           category TEXT NOT NULL DEFAULT 'Uncategorized',
                           source TEXT,
                           external_id TEXT UNIQUE,
                           created_at TEXT NOT NULL DEFAULT (datetime('now'))
                        )
                    """)
    connection.execute('CREATE INDEX IF NOT EXISTS index_tx_date ON transactions(tx_date)')
    connection.commit()
    
    
def insert_transaction(
    connection: sqlite3.Connection, 
    tx_date: str, 
    amount: float, 
    name: str | None = None, 
    description: str | None = None, 
    category: str = 'Uncategorized',
    source: str | None = None, 
    external_id: str | None = None,
    ) -> int | None:
    inserted_rows = connection.execute(
        """
        INSERT OR IGNORE INTO transactions (tx_date, amount, name, description, category, source, external_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (tx_date, amount, name, description, category, source, external_id)
    )
    connection.commit()
    return inserted_rows.lastrowid if inserted_rows.rowcount else None
    
    
def list_transactions( #todo: category
    connection: sqlite3.Connection, 
    start_date: str | None = None, 
    end_date: str | None = None, 
    tx_type: str = 'All', 
    limit: int = 200,
    ):
    
    where = []
    params = []
    
    if start_date:
        where.append ('tx_date >= ?')
        params.append(start_date)
    if end_date:
        where.append ('tx_date <= ?')
        params.append(end_date)
    
    if tx_type == 'Expenses':
        where.append('amount < 0')
    elif tx_type == 'Income':
        where.append('amount > 0')
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    
    query = connection.execute( #info todo 
        f"""
        SELECT id, 
        tx_date AS date,
        amount, 
        category, 
        '' AS info 
        FROM transactions
        {where_sql}
        ORDER BY tx_date DESC, id DESC
        LIMIT ?
        """, (*params, limit) #category and info placeholder still
    )
    return [dict(row) for row in query.fetchall()]
    

def update_transaction_category(connection: sqlite3.Connection, tx_id: int, category: str) -> None:
    connection.execute(
        'UPDATE transactions SET category = ? WHERE id = ?',
        (category, tx_id)
    )
    connection.commit()
    
def get_categories(connection: sqlite3.Connection) -> list[str]:
    query = connection.execute(
        """
        SELECT DISTINCT category 
        FROM transactions
        ORDER BY category COLLATE NOCASE
        """
    )
    return [row['category'] for row in query.fetchall()]

def get_all_transactions(connection):
    query = connection.execute(
        "SELECT id, tx_date, amount FROM transactions"
    )
    return query.fetchall()


# _____testing______

def insert_test_transaction(connection: sqlite3.Connection) -> None:
    test_transactions = [
        # -------------------------
        # THIS MONTH (Dec 2025)
        # -------------------------
        ("2025-12-01", 2500.00, "Employer Inc.", "Salary December", "Income"),
        ("2025-12-02", -42.60, "Life", "Groceries", "Groceries"),
        ("2025-12-03", -9.99, "Spotify", "Monthly Subscription", "Subscriptions"),
        ("2025-12-05", -4.80, "Starbucks", "Coffee", "Food"),
        ("2025-12-07", -29.00, "JR", "Monthly Ticket", "Transport"),
        ("2025-12-09", -18.50, "Cinema", "Movie night", "Leisure"),
        ("2025-12-12", -79.90, "Amazon", "USB-C Hub", "Shopping"),
        ("2025-12-15", -12.99, "Netflix", "Monthly Subscription", "Subscriptions"),
        ("2025-12-18", -23.40, "Icchan Ramen", "Dinner", "Food"),
        ("2025-12-19", 120.00, "Friend", "Payback split bills", "Income"),

        # -------------------------
        # LAST 30 DAYS, but NOT THIS MONTH (Nov 19–Nov 30 2025)
        # -------------------------
        ("2025-11-19", -15.20, "Sun Drug", "Toiletries", "Groceries"),
        ("2025-11-21", -8.90, "Bakery", "Breakfast", "Food"),
        ("2025-11-24", -52.10, "Life", "Groceries", "Groceries"),
        ("2025-11-26", -12.50, "Uber", "Ride home", "Transport"),
        ("2025-11-29", -34.99, "Zara", "Clothes", "Shopping"),

        # -------------------------
        # THIS YEAR (2025) but NOT LAST 30 DAYS (earlier in 2025)
        # -------------------------
        ("2025-10-03", 2500.00, "Employer Inc.", "Salary October", "Income"),
        ("2025-10-06", -61.75, "Fresco", "Groceries", "Groceries"),
        ("2025-09-14", -120.00, "Dentist", "Checkup co-pay", "Health"),
        ("2025-07-22", -18.50, "Bowling Center", "Bowling", "Leisure"),
        ("2025-03-10", -29.90, "Steam", "Game", "Leisure"),

        # -------------------------
        # NOT THIS YEAR (2024)
        # -------------------------
        ("2024-12-28", -55.00, "Uniqlo", "Winter clothes", "Shopping"),
        ("2024-11-15", 200.00, "Tax Office", "Refund", "Income"),
        ("2024-06-02", -450.00, "Landlord", "Deposit top-up", "Housing"),
    ]

    for tx_date, amount, name, description, category in test_transactions:
        insert_transaction(
            connection=connection,
            tx_date=tx_date,
            amount=amount,
            name=name,
            description=description,
            category=category,
            source="test_data",
        )
