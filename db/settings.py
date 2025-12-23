import sqlite3


def init_settings_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.commit()


def set_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    connection.commit()


def get_setting(connection: sqlite3.Connection, key: str) -> str | None:
    cursor = connection.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,),
    )
    row = cursor.fetchone()
    return row["value"] if row else None
