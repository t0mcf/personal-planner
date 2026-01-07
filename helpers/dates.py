from datetime import date
import calendar

def last_day_of_month(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)

def valid_day(year: int, month: int, day: int) -> int:
    last_date = last_day_of_month(year, month)
    last_day = last_date.day
    if day < 1:
        return 1
    if day > last_day:
        return last_day
    return day

def month_range(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end
