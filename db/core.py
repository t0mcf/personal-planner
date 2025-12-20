import sqlite3
from pathlib import Path
from db.finance import init_finance_tables

DB_PATH = Path('data') / 'planner.db'

def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    init_finance_tables(connection)