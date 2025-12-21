import sqlite3
from datetime import date as dt_date


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




#intended for usage with the calendar view to get info whether journaling has been done
def get_journal_days_for_month(connection, year: int, month: int) -> set[str]:
    start_date = dt_date(year, month, 1)

    if month == 12:
        end_date = dt_date(year + 1, 1, 1)
    else:
        end_date = dt_date(year, month + 1, 1)

    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT date
        FROM journal
        WHERE date >= ?
          AND date < ?
          AND text IS NOT NULL
          AND TRIM(text) != ''
        ''',
        (start_iso, end_iso),
    )

    return {row[0] for row in cursor.fetchall()}
