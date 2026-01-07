from datetime import date as dt_date

from db.xp import get_total_xp, level_for_total_xp, count_xp_events_by_type, count_positive_xp_events_by_type
from db.habits import list_active_habits, get_daily_streak, get_weekly_streak
from db.finance import has_spendthrift_transaction, has_breadwinner_transaction

def _max_daily_streak(connection, day: str) -> int:
    best = 0
    for h in list_active_habits(connection):
        hid = int(h.get("id") or 0)
        if hid:
            best = max(best, int(get_daily_streak(connection, hid, day) or 0))
    return best

def _max_weekly_streak(connection, day: str) -> int:
    best = 0
    for h in list_active_habits(connection):
        hid = int(h.get("id") or 0)
        if hid:
            best = max(best, int(get_weekly_streak(connection, hid, day) or 0))
    return best

def check_level_at_least(n: int):
    return lambda c, day=None: level_for_total_xp(get_total_xp(c))[0] >= n

def check_todo_count(n: int):
    return lambda c, day=None: count_positive_xp_events_by_type(c, "todo_completed") >= n

def check_journal_count(n: int):
    return lambda c, day=None: count_xp_events_by_type(c, "journal_written") >= n

def check_daily_streak_at_least(n: int):
    return lambda c, day=None: _max_daily_streak(c, (day or dt_date.today().isoformat())) >= n

def check_weekly_streak_at_least(n: int):
    return lambda c, day=None: _max_weekly_streak(c, (day or dt_date.today().isoformat())) >= n

CHECKS = {
    "level_5": check_level_at_least(5),
    "level_25": check_level_at_least(25),
    "level_50": check_level_at_least(50),
    "level_100": check_level_at_least(100),

    "daily_streak_7": check_daily_streak_at_least(7),
    "daily_streak_30": check_daily_streak_at_least(30),
    "weekly_streak_4": check_weekly_streak_at_least(4),
    "weekly_streak_12": check_weekly_streak_at_least(12),

    "todos_10": check_todo_count(10),
    "todos_50": check_todo_count(50),
    "todos_200": check_todo_count(200),

    "journal_first": check_journal_count(1),
    "journal_30": check_journal_count(30),

    "spendthrift": lambda c, day=None: has_spendthrift_transaction(c, 1000000),
    "breadwinner": lambda c, day=None: has_breadwinner_transaction(c, 1000000),
}
