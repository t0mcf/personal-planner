import sqlite3


def init_journal_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            date TEXT PRIMARY KEY, -- YYYY-MM-DD
            text TEXT NOT NULL
        )
    """)
    connection.commit()


def get_journal_entry(
    connection: sqlite3.Connection,
    date: str,
) -> str | None:
    cursor = connection.execute(
        """
        SELECT text
        FROM journal
        WHERE date = ?
        """,
        (date,),
    )
    row = cursor.fetchone()
    return row["text"] if row else None


def save_journal_entry(
    connection: sqlite3.Connection,
    date: str,
    text: str,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO journal (date, text)
        VALUES (?, ?)
        """,
        (date, text),
    )
    connection.commit()
