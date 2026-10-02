"""Общие настройки приложения."""

from pathlib import Path

# Файл БД лежит в корне проекта рядом с main.py.
DB_PATH = Path(__file__).resolve().parent.parent / "gm_hub.db"

# Формат хранения даты и времени в БД (п. 4.3.2 ТЗ).
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
