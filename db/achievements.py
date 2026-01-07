import sqlite3

DEFAULT_ACHIEVEMENTS = [
    # levels
    ("level_5", "Getting Started", "Reach level 5", 0, "progress", 10),
    ("level_25", "Committed", "Reach level 25", 0, "progress", 20),
    ("level_50", "Lifestyle", "Reach level 50", 0, "progress", 30),
    ("level_100", "Addict", "Reach level 100", 0, "progress", 40),

    # streaks
    ("daily_streak_7", "Locked In", "Maintain a 7-day daily streak", 0, "habits", 100),
    ("daily_streak_30", "Routine Built", "Maintain a 30-day daily streak", 0, "habits", 110),
    ("weekly_streak_4", "Weekly Grind", "Maintain a 4-week streak", 0, "habits", 120),
    ("weekly_streak_12", "No Excuses", "Maintain a 12-week streak", 0, "habits", 130),

    # todos
    ("todos_10", "Little Wins", "Complete 10 to-dos", 0, "todos", 200),
    ("todos_50", "Handling Business", "Complete 50 to-dos", 0, "todos", 210),
    ("todos_200", "Heavy Lifting", "Complete 200 to-dos", 0, "todos", 220),

    # journal
    ("journal_first", "First Entry", "Write your first journal entry", 0, "journal", 300),
    ("journal_30", "Archive", "Write journal entries on 30 days", 0, "journal", 320),

    # finance more unserious stuff (big transactions for now)
    ("spendthrift", "Spendthrift", "Spend at least ¥1,000,000 in a single transaction", 1, "finance", 400),
    ("breadwinner", "Breadwinner", "Receive at least ¥1,000,000 in a single transaction", 1, "finance", 410),

]

def init_achievement_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS achievements (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            hidden_description INTEGER NOT NULL DEFAULT 0,
            category TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS achievements_unlocked (
            achievement_id TEXT PRIMARY KEY,
            unlocked_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (achievement_id) REFERENCES achievements(id)
        )
        """
    )
    connection.commit()

def seed_default_achievements(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO achievements (id, name, description, hidden_description, category, sort_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        DEFAULT_ACHIEVEMENTS,
    )
    connection.commit()

def list_achievements(connection: sqlite3.Connection) -> list[dict]:
    cur = connection.execute(
        """
        SELECT id, name, description, hidden_description, category, sort_order
        FROM achievements
        ORDER BY sort_order ASC, id ASC
        """
    )
    return [dict(r) for r in cur.fetchall()]

def list_unlocked_ids(connection: sqlite3.Connection) -> set[str]:
    cur = connection.execute("SELECT achievement_id FROM achievements_unlocked")
    return {str(r["achievement_id"]) for r in cur.fetchall()}

def unlock(connection: sqlite3.Connection, achievement_id: str) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO achievements_unlocked (achievement_id) VALUES (?)",
        (achievement_id,),
    )
    connection.commit()
