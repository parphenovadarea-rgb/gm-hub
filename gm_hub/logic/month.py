"""Календарь месяца: сетка дней для выбора даты и вкладки «Календарь»."""

import calendar
from datetime import date, datetime

from gm_hub.config import DATETIME_FORMAT

MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]  # fmt: skip
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def month_grid(year: int, month: int) -> list:
    """Недели месяца с понедельника, как в обычном календаре.

    Args:
        year: Год.
        month: Месяц (1–12).

    Returns:
        Список недель; неделя — 7 дат. Дни соседних месяцев заменены на None.
    """
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    return [[day if day.month == month else None for day in week] for week in weeks]


def shift_month(year: int, month: int, delta: int) -> tuple:
    """Соседний месяц: delta = 1 — следующий, -1 — предыдущий.

    Returns:
        Пара (год, месяц).
    """
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def games_by_day(games) -> dict:
    """Раскладывает сессии по дням.

    Args:
        games: Строки сессий с полем scheduled_at.

    Returns:
        Словарь {дата: [сессии этого дня по времени]}.
    """
    days = {}
    for game in sorted(games, key=lambda g: g["scheduled_at"]):
        day = datetime.strptime(game["scheduled_at"], DATETIME_FORMAT).date()
        days.setdefault(day, []).append(game)
    return days


def title(year: int, month: int) -> str:
    """Подпись месяца: «Октябрь 2026»."""
    return f"{MONTH_NAMES[month - 1]} {year}"


def today() -> date:
    """Сегодняшняя дата (отдельная функция — её удобно подменять в тестах)."""
    return date.today()
