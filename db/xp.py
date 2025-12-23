import sqlite3
from datetime import date as dt_date, datetime, timedelta

#source id is the id of whatever triggered this (todo id, habit id or similar)
#soure date is the date of the event that triggered this (for example the date of this todo), maybe unnecessary but ill keep this for now
def init_xp_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS xp_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            event_type TEXT NOT NULL,
            xp_amount INTEGER NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            source_id INTEGER,
            source_date TEXT
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS index_xp_events_created_at ON xp_events(created_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS index_xp_events_type_date ON xp_events(event_type, source_date)"
    )
    connection.commit()


def add_xp_event(
    connection: sqlite3.Connection,
    event_type: str,
    xp_amount: int,
    message: str,
    source_id: int | None = None,
    source_date: str | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO xp_events (event_type, xp_amount, message, source_id, source_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_type, xp_amount, message, source_id, source_date),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_total_xp(connection: sqlite3.Connection) -> int:
    cursor = connection.execute(
        "SELECT COALESCE(SUM(xp_amount), 0) AS total FROM xp_events"
    )
    row = cursor.fetchone()
    return int(row['total'] or 0)


def list_recent_xp_events(connection: sqlite3.Connection, limit: int = 25) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT id, created_at, event_type, xp_amount, message, source_id, source_date
        FROM xp_events
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


def has_xp_event_for_day(connection: sqlite3.Connection, event_type: str, day: str) -> bool:
    cursor = connection.execute(
        """
        SELECT 1
        FROM xp_events
        WHERE event_type = ?
          AND source_date = ?
        LIMIT 1
        """,
        (event_type, day),
    )
    return cursor.fetchone() is not None


def week_start_iso(day_iso: str) -> str:
    day = dt_date.fromisoformat(day_iso)
    # monday as start
    start = day - timedelta(days=day.weekday())
    return start.isoformat()


def has_weekly_reward(connection: sqlite3.Connection, habit_id: int, week_start: str) -> bool:
    cursor = connection.execute(
        """
        SELECT 1
        FROM xp_events
        WHERE event_type = 'weekly_habit_target_reached'
          AND source_id = ?
          AND source_date = ?
        LIMIT 1
        """,
        (habit_id, week_start),
    )
    return cursor.fetchone() is not None


# level curve (progressive)
# level 1 starts at 0 xp
# to go from level n -> n+1 you need round(100 * 1.2^(n-1))
def xp_needed_for_level(level: int) -> int:
    if level <= 1:
        return 0
    needed = 100
    for _ in range(level - 2):
        needed = int(round(needed * 1.2))
    return needed


def xp_needed_for_next_level(level: int) -> int:
    # xp needed to go from current level -> next level
    if level < 1:
        level = 1
    needed = 100
    for _ in range(level - 1):
        needed = int(round(needed * 1.2))
    return needed


def level_for_total_xp(total_xp: int) -> tuple[int, int, int]:
    # returns (level, xp_into_level, xp_to_next)
    if total_xp < 0:
        total_xp = 0

    level = 1
    remaining = total_xp

    while True:
        step = xp_needed_for_next_level(level)
        if remaining >= step:
            remaining -= step
            level += 1
        else:
            return (level, remaining, step)


def badge_tier_for_level(level: int) -> int:
    if level >= 100:
        return 4
    if level >= 50:
        return 3
    if level >= 25:
        return 2
    if level >= 10:
        return 1
    return 0


def next_badge_milestone(level: int) -> int | None:
    if level < 10:
        return 10
    if level < 25:
        return 25
    if level < 50:
        return 50
    if level < 100:
        return 100
    return None
