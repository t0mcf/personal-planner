from db.todos import set_todo_completed, get_todo_title
from db.habits import (
    set_daily_done,
    increment_habit_today,
    get_weekly_progress,
    get_habit_title,
)
from db.journal import save_journal_entry

from actions.xp_rules import (
    todo_toggled,
    daily_habit_toggled,
    weekly_habit_target_reached,
    journal_written,
)


def toggle_todo(
    connection,
    day: str,
    todo_id: int,
    completed: bool,
) -> None:
    title = get_todo_title(connection, todo_id)
    set_todo_completed(connection, todo_id, completed)
    todo_toggled(connection, day, todo_id, title, completed)


def toggle_daily_habit(
    connection,
    day: str,
    habit_id: int,
    done: bool,
) -> None:
    title = get_habit_title(connection, habit_id)
    set_daily_done(connection, habit_id, day, done)
    daily_habit_toggled(connection, day, habit_id, title, done)


def increment_weekly_habit(
    connection,
    day: str,
    habit_id: int,
) -> None:
    title = get_habit_title(connection, habit_id)
    increment_habit_today(connection, habit_id, day)
    new_done, target = get_weekly_progress(connection, habit_id, day)
    weekly_habit_target_reached(connection, day, habit_id, title, new_done, target)


def save_journal(
    connection,
    day: str,
    text: str,
) -> None:
    save_journal_entry(connection, day, text)
    journal_written(connection, day, text)
