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
    connection.commit()
    
    
def insert_transaction(
    connection, tx_date, amount, 
    name=None, description=None, category='Uncategorized',
    source=None, external_id=None):
    inserted_rows = connection.execute(
        """
        INSERT INTO transactions (tx_date, amount, name, description, category, source, external_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (tx_date, amount, name, description, category, source, external_id)
    )
    connection.commit()
    return inserted_rows.lastrowid
    
    
def list_transactions(connection, start_date=None, end_date=None, tx_type = 'All', limit=200):
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
    
    sel = connection.execute(
        f"""
        SELECT tx_date AS date,
        amount AS amount, 
        'Uncategorized' AS category, 
        '' AS info
        FROM transactions
        {where_sql}
        ORDER BY tx_date DESC, id DESC
        LIMIT ?
        """, (*params, limit) #category and info placeholder still
    )
    return [dict(row) for row in sel.fetchall()]
    
    
def insert_test_transaction(connection):
    #connection.execute(
    #    "INSERT INTO transactions (tx_date, amount) VALUES (?, ?)",
     #   ("2025-11-21", -12.50)
    #)
    insert_transaction(
        connection,
        tx_date="2025-11-21",
        amount=100,
        name='Starbucks',
        description='coffee'
        )
    insert_transaction(
        connection,
        tx_date="2024-11-21",
        amount=100,
        name='Starbucks',
        description='coffee'
        )
    insert_transaction(
        connection,
        tx_date="2025-10-20",
        amount=100,
        name='Starbucks',
        description='coffee'
        )
    

def get_all_transactions(connection):
    cursor = connection.execute(
        "SELECT id, tx_date, amount FROM transactions"
    )
    return cursor.fetchall()