import sqlite3


def init_todo_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT, -- YYYY-MM-DD, NULL = no specific day
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS index_todos_date ON todos(date)"
    )
    connection.commit()


def insert_todo(
    connection: sqlite3.Connection,
    title: str,
    date: str | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO todos (title, date)
        VALUES (?, ?)
        """,
        (title, date),
    )
    connection.commit()
    return cursor.lastrowid


def list_todos_for_day(
    connection: sqlite3.Connection,
    date: str,
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT id, title, completed
        FROM todos
        WHERE date = ?
        ORDER BY completed ASC, id ASC
        """,
        (date,),
    )
    return [dict(row) for row in cursor.fetchall()]


def list_all_todos(
    connection: sqlite3.Connection,
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT id, title, date, completed
        FROM todos
        ORDER BY 
            CASE WHEN date IS NULL THEN 1 ELSE 0 END,
            date ASC,
            completed ASC,
            id ASC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def set_todo_completed(
    connection: sqlite3.Connection,
    todo_id: int,
    completed: bool,
) -> None:
    connection.execute(
        """
        UPDATE todos
        SET completed = ?
        WHERE id = ?
        """,
        (1 if completed else 0, todo_id),
    )
    connection.commit()


def delete_todo(
    connection: sqlite3.Connection,
    todo_id: int,
) -> None:
    connection.execute(
        "DELETE FROM todos WHERE id = ?",
        (todo_id,),
    )
    connection.commit()
