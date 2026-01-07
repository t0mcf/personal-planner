from db.xp import add_xp_event, has_xp_event_for_day, has_weekly_reward, week_start_iso


TODO_XP = 20
DAILY_HABIT_XP = 20
WEEKLY_HABIT_XP = 50
JOURNAL_XP = 10


def todo_toggled(
    connection,
    day: str,
    todo_id: int,
    title: str,
    completed: bool,
) -> None:
    xp_amount = TODO_XP if completed else -TODO_XP
    add_xp_event(
        connection,
        'todo_completed',
        xp_amount,
        f'todo: {title}',
        source_id=todo_id,
        source_date=day,
    )


def daily_habit_toggled(
    connection,
    day: str,
    habit_id: int,
    title: str,
    done: bool,
) -> None:
    xp_amount = DAILY_HABIT_XP if done else -DAILY_HABIT_XP
    add_xp_event(
        connection,
        'daily_habit_done',
        xp_amount,
        f'habit: {title}',
        source_id=habit_id,
        source_date=day,
    )


def weekly_habit_target_reached(
    connection,
    day: str,
    habit_id: int,
    title: str,
    new_done: int,
    target: int,
) -> None:
    if not target:
        return

    if new_done < target:
        return

    week_start = week_start_iso(day)

    if has_weekly_reward(connection, habit_id, week_start):
        return

    add_xp_event(
        connection,
        'weekly_habit_target_reached',
        WEEKLY_HABIT_XP,
        f'weekly target reached: {title}',
        source_id=habit_id,
        source_date=week_start,
    )


def journal_written(connection, day: str, text: str) -> None:
    if not text.strip():
        return

    if has_xp_event_for_day(connection, 'journal_written', day):
        return

    add_xp_event(
        connection,
        'journal_written',
        JOURNAL_XP,
        'journal written',
        source_date=day,
    )
