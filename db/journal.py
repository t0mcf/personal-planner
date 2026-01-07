import sqlite3
from helpers.dates import month_range


def init_journal_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            date TEXT PRIMARY KEY, 

            text TEXT NOT NULL DEFAULT '',

            mood INTEGER,
            sleep INTEGER,  

            went_well TEXT NOT NULL DEFAULT '',
            difficult TEXT NOT NULL DEFAULT '',
            remember TEXT NOT NULL DEFAULT ''
        )
    """)
    connection.commit()

#still all compatible with previous version but maybe check if smth is redundant now 
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
    mood: int | None = None,
    sleep: int | None = None,
    went_well: str | None = None,
    difficult: str | None = None,
    remember: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO journal (date, text)
        VALUES (?, COALESCE(?, ''))
        """,
        (date, text),
    )

    fields = []
    params: list = []

    fields.append("text = ?")
    params.append(text or "")

    if mood is not None:
        fields.append("mood = ?")
        params.append(int(mood))

    if sleep is not None:
        fields.append("sleep = ?")
        params.append(int(sleep))

    if went_well is not None:
        fields.append("went_well = ?")
        params.append(went_well or "")

    if difficult is not None:
        fields.append("difficult = ?")
        params.append(difficult or "")

    if remember is not None:
        fields.append("remember = ?")
        params.append(remember or "")

    params.append(date)

    connection.execute(
        f"""
        UPDATE journal
        SET {", ".join(fields)}
        WHERE date = ?
        """,
        params,
    )
    connection.commit()

def get_journal_data(connection: sqlite3.Connection, date: str) -> dict | None:
    cursor = connection.execute(
        """
        SELECT date, text, mood, sleep, went_well, difficult, remember
        FROM journal
        WHERE date = ?
        """,
        (date,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


# intended for usage with the calendar view
def get_journal_status_for_month(connection, year: int, month: int) -> dict[str, bool]:
    start_date, end_date = month_range(year, month)

    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT date, text, mood, sleep, went_well, difficult, remember
        FROM journal
        WHERE date >= ?
        AND date < ?
        """,
        (start_iso, end_iso),
    )

    status: dict[str, bool] = {}
    for day, text, mood, sleep, went_well, difficult, remember in cursor.fetchall():
        has_text = bool((text or '').strip()) \
            or bool((went_well or '').strip()) \
            or bool((difficult or '').strip()) \
            or bool((remember or '').strip())

        status[str(day)] = has_text

    return status

def get_journal_mood_for_month(connection, year: int, month: int) -> dict[str, int]:
    start_date, end_date = month_range(year, month)

    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT date, mood
        FROM journal
        WHERE date >= ?
        AND date < ?
        AND mood IS NOT NULL
        """,
        (start_iso, end_iso),
    )

    moods: dict[str, int] = {}
    for day, mood in cursor.fetchall():
        try:
            moods[str(day)] = int(mood)
        except Exception:
            continue

    return moods
