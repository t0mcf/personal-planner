from datetime import date as dt_date, timedelta

#frequency is supposed to be 'daily' or 'weekly'
#weekly_target only for weekly (e.g. 3 workouts)
#active if we want to provide on and off switching (1=active, 0=inactive)
#habit log for streaks etc
def init_habit_tables(connection):
    connection.execute("""
                       CREATE TABLE IF NOT EXISTS habits(
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT NOT NULL,
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
    
    
def list_active_habits(connection) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT id, title, frequency, weekly_target, start_date
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
            'frequency': row[2],
            'weekly_target': row[3],
            'start_date': row[4],
        })

    return habits


#intended for daily habit use, maybe restrict to that 
def set_daily_done(connection, habit_id: int, day: str, done: bool):
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
def is_daily_done(connection, habit_id: int, day: str) -> bool:
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
def get_weekly_progress(connection, habit_id: int, day: str) -> tuple[int, int]:
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
def decrement_habit_today(connection, habit_id: int, day: str):
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
def is_weekly_done(connection, habit_id: int, day: str) -> bool:
    done, target = get_weekly_progress(connection, habit_id, day)
    if not target:
        return False
    return done >= target



#daily streak calculation (first draft)
def get_daily_streak(connection, habit_id: int, as_of_day: str) -> int:
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
