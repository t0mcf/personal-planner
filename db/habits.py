from datetime import date as dt_date, timedelta
from helpers.dates import month_range
import sqlite3


#frequency is supposed to be 'daily' or 'weekly'
#weekly_target only for weekly (e.g. 3 workouts)
#active if we want to provide on and off switching (1=active, 0=inactive)
#habit log for streaks etc
def init_habit_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""
                       CREATE TABLE IF NOT EXISTS habits(
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT NOT NULL,
                           emoji TEXT, 
                           frequency TEXT NOT NULL,
                           weekly_target INTEGER,
                           active INTEGER NOT NULL DEFAULT 1,
                           start_date TEXT
                        )
                    """)
    connection.execute("""
                       CREATE TABLE IF NOT EXISTS habit_log(
                           habit_id INTEGER NOT NULL,
                           date TEXT NOT NULL,
                           count INTEGER NOT NULL,
                           PRIMARY KEY (habit_id, date),
                           FOREIGN KEY (habit_id) REFERENCES habits(id)
                        )
                    """)
    connection.execute('CREATE INDEX IF NOT EXISTS index_habit_log_habit_date ON habit_log (habit_id, date)')
    connection.commit()
    
    
def list_active_habits(connection: sqlite3.Connection) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT id, title, emoji, frequency, weekly_target, start_date
        FROM habits
        WHERE active = 1
        ORDER BY id
        '''
    )

    rows = cursor.fetchall()
    habits = []

    for row in rows:
        habits.append({
            'id': row[0],
            'title': row[1],
            'emoji': row[2],
            'frequency': row[3],
            'weekly_target': row[4],
            'start_date': row[5],
        })

    return habits


#intended for daily habit use, maybe restrict to that 
def set_daily_done(connection: sqlite3.Connection, habit_id: int, day: str, done: bool) -> None:
    cursor = connection.cursor()

    if done:
        cursor.execute(
            '''
            INSERT OR REPLACE INTO habit_log (habit_id, date, count)
            VALUES (?, ?, 1)
            ''',
            (habit_id, day),
        )
    else:
        cursor.execute(
            '''
            DELETE FROM habit_log
            WHERE habit_id = ? AND date = ?
            ''',
            (habit_id, day),
        )

    connection.commit()


#intended for weekly habit
def increment_habit_today(connection, habit_id: int, day: str):
    cursor = connection.cursor()

    cursor.execute(
        '''
        INSERT INTO habit_log (habit_id, date, count)
        VALUES (?, ?, 1)
        ON CONFLICT(habit_id, date)
        DO UPDATE SET count = count + 1
        ''',
        (habit_id, day),
    )

    connection.commit()


#fetch if a certain habit is completed
def is_daily_done(connection: sqlite3.Connection, habit_id: int, day: str) -> bool:
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT count
        FROM habit_log
        WHERE habit_id = ? AND date = ?
        ''',
        (habit_id, day),
    )

    row = cursor.fetchone()
    return bool(row and row[0] >= 1)


#important for streaks to compare whether weekly progress >= goal and for daily display
#deprecated progrably
def get_weekly_progress(connection: sqlite3.Connection, habit_id: int, day: str) -> tuple[int, int]:
    day_date = dt_date.fromisoformat(day)

    week_start = day_date - timedelta(days=day_date.weekday())  # Monday
    week_end = week_start + timedelta(days=6)

    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT SUM(count)
        FROM habit_log
        WHERE habit_id = ?
          AND date >= ?
          AND date <= ?
        ''',
        (
            habit_id,
            week_start.isoformat(),
            week_end.isoformat(),
        ),
    )

    done = cursor.fetchone()[0] or 0

    cursor.execute(
        '''
        SELECT weekly_target
        FROM habits
        WHERE id = ?
        ''',
        (habit_id,),
    )

    target = cursor.fetchone()[0]
    return done, target


#have to think about whether this may destroy logic, maybe remove again
def decrement_habit_today(connection: sqlite3.Connection, habit_id: int, day: str) -> None:
    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT count
        FROM habit_log
        WHERE habit_id = ? AND date = ?
        ''',
        (habit_id, day),
    )
    row = cursor.fetchone()
    if not row:
        return

    count = int(row[0])
    if count <= 1:
        cursor.execute(
            '''
            DELETE FROM habit_log
            WHERE habit_id = ? AND date = ?
            ''',
            (habit_id, day),
        )
    else:
        cursor.execute(
            '''
            UPDATE habit_log
            SET count = count - 1
            WHERE habit_id = ? AND date = ?
            ''',
            (habit_id, day),
        )

    connection.commit()



#wrapper, maybe useful, might remove if not used later on
#deprecated prolly
def is_weekly_done(connection: sqlite3.Connection, habit_id: int, day: str) -> bool:
    done, target = get_weekly_progress(connection, habit_id, day)
    if not target:
        return False
    return done >= target



#daily streak calculation 
def get_daily_streak(connection: sqlite3.Connection, habit_id: int, as_of_day: str) -> int:
    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT start_date
        FROM habits
        WHERE id = ?
        ''',
        (habit_id,),
    )
    row = cursor.fetchone()
    start_date = row[0]

    current = dt_date.fromisoformat(as_of_day)
    streak = 0

    while True:
        day_iso = current.isoformat()

        if start_date and day_iso < start_date:
            break

        cursor.execute(
            '''
            SELECT count
            FROM habit_log
            WHERE habit_id = ? AND date = ?
            ''',
            (habit_id, day_iso),
        )

        row = cursor.fetchone()
        if not row or row[0] < 1:
            break

        streak += 1
        current -= timedelta(days=1)

    return streak


def get_weekly_streak(connection: sqlite3.Connection, habit_id: int, as_of_day: str) -> int:
    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT weekly_target, start_date
        FROM habits
        WHERE id = ?
        ''',
        (habit_id,),
    )
    row = cursor.fetchone()
    if not row:
        return 0

    target = int(row[0] or 0)
    start_date = row[1]
    if target <= 0:
        return 0

    current = dt_date.fromisoformat(as_of_day)
    streak = 0

    while True:
        week_start = current - timedelta(days=current.weekday())  #monday
        week_end = week_start + timedelta(days=6)

        if start_date and week_end.isoformat() < start_date:
            break

        cursor.execute(
            '''
            SELECT SUM(count)
            FROM habit_log
            WHERE habit_id = ?
              AND date >= ?
              AND date <= ?
            ''',
            (habit_id, week_start.isoformat(), week_end.isoformat()),
        )
        done = int(cursor.fetchone()[0] or 0)

        if done < target:
            break

        streak += 1
        current = week_start - timedelta(days=1)  #go to previous week

    return streak


def get_daily_habit_stats_for_month(connection: sqlite3.Connection, year: int, month: int) -> tuple[int, dict[str, int]]:
    start_date, end_date = month_range(year, month)

    cursor = connection.cursor()

    cursor.execute(
        '''
        SELECT COUNT(*)
        FROM habits
        WHERE active = 1 AND frequency = 'daily'
        '''
    )
    total_daily = int(cursor.fetchone()[0] or 0)

    if total_daily == 0:
        return 0, {}

    cursor.execute(
        '''
        SELECT hl.date, COUNT(*) AS done_count
        FROM habit_log hl
        JOIN habits h ON h.id = hl.habit_id
        WHERE h.active = 1
        AND h.frequency = 'daily'
        AND hl.count >= 1
        AND hl.date >= ?
        AND hl.date < ?
        GROUP BY hl.date
        ''',
        (start_date.isoformat(), end_date.isoformat()),
    )

    done_by_day: dict[str, int] = {}
    for row in cursor.fetchall():
        day = row[0]
        done_count = int(row[1] or 0)
        done_by_day[str(day)] = done_count

    return total_daily, done_by_day

def insert_habit(
    connection: sqlite3.Connection,
    title: str,
    emoji: str | None,
    frequency: str,
    weekly_target: int | None,
    active: bool,
    start_date: str | None,
) -> int:
    cursor = connection.execute(
        '''
        INSERT INTO habits (title, emoji, frequency, weekly_target, active, start_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (
            title,
            emoji,
            frequency,
            weekly_target,
            1 if active else 0,
            start_date,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_all_habits(connection: sqlite3.Connection) -> list[dict]:
    cursor = connection.execute(
        '''
        SELECT id, title, emoji, frequency, weekly_target, active, start_date
        FROM habits
        ORDER BY active DESC, id ASC
        '''
    )
    return [dict(row) for row in cursor.fetchall()]


def set_habit_active(
    connection: sqlite3.Connection,
    habit_id: int,
    active: bool,
) -> None:
    connection.execute(
        '''
        UPDATE habits
        SET active = ?
        WHERE id = ?
        ''',
        (1 if active else 0, habit_id),
    )
    connection.commit()


def delete_habit(connection: sqlite3.Connection, habit_id: int) -> None:
    connection.execute(
        'DELETE FROM habit_log WHERE habit_id = ?',
        (habit_id,),
    )
    connection.execute(
        'DELETE FROM habits WHERE id = ?',
        (habit_id,),
    )
    connection.commit()
    

def update_habit(
    connection: sqlite3.Connection,
    habit_id: int,
    title: str,
    emoji: str | None,
    frequency: str,
    weekly_target: int | None,
    start_date: str | None,
) -> None:
    connection.execute(
        '''
        UPDATE habits
        SET title = ?, emoji = ?, frequency = ?, weekly_target = ?, start_date = ?
        WHERE id = ?
        ''',
        (
            title,
            emoji,
            frequency,
            weekly_target,
            start_date,
            habit_id,
        ),
    )
    connection.commit()
    
    
def get_habit_title(connection: sqlite3.Connection, habit_id: int) -> str:
    cursor = connection.execute(
        """
        SELECT title
        FROM habits
        WHERE id = ?
        """,
        (habit_id,),
    )
    row = cursor.fetchone()
    return row['title'] if row else ''

