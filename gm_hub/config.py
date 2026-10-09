"""Общие настройки приложения."""

import sys
from datetime import datetime
from pathlib import Path

# Файл БД лежит в корне проекта рядом с main.py, а в собранной программе
# (GameMasterHub.exe) — рядом с exe, чтобы данные сохранялись между запусками.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "gm_hub.db"

# Формат хранения даты и времени в БД (п. 4.3.2 ТЗ).
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

# Формат, в котором дата показывается и вводится в окнах.
SHOW_FORMAT = "%d.%m.%Y %H:%M"


def now_str() -> str:
    """Возвращает текущие дату и время в формате БД.

    Returns:
        Строка вида «2026-10-04 18:00».
    """
    return datetime.now().strftime(DATETIME_FORMAT)


def to_show(db_value: str | None) -> str:
    """Переводит дату из формата БД в формат для окна.

    Args:
        db_value: Дата в формате БД или None.

    Returns:
        Строка вида «04.10.2026 18:00» или «—», если даты нет.
    """
    if not db_value:
        return "—"
    return datetime.strptime(db_value, DATETIME_FORMAT).strftime(SHOW_FORMAT)


def to_short(db_value: str | None) -> str:
    """Переводит дату из формата БД в короткий вид без года.

    Args:
        db_value: Дата в формате БД или None.

    Returns:
        Строка вида «04.10 18:00» или «—», если даты нет.
    """
    if not db_value:
        return "—"
    return datetime.strptime(db_value, DATETIME_FORMAT).strftime("%d.%m %H:%M")
