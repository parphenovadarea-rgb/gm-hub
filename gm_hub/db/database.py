"""Подключение к базе данных SQLite."""

import sqlite3
from pathlib import Path

from gm_hub.config import DB_PATH

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path=DB_PATH) -> sqlite3.Connection:
    """Открывает БД и включает проверку внешних ключей.

    Args:
        path: Путь к файлу БД. Для тестов можно передать ":memory:".

    Returns:
        Подключение, в котором строки можно читать по имени столбца.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Проверка внешних ключей включается при каждом подключении (п. 4.3.2 ТЗ).
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Создаёт таблицы, если их ещё нет.

    Args:
        conn: Подключение к БД.
    """
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    # В БД, созданной до разделения Мастеров, у World_Notes нет gm_id —
    # добавляем столбец, чтобы старый файл БД продолжил работать.
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(World_Notes)")]
    if "gm_id" not in columns:
        with conn:
            conn.execute(
                "ALTER TABLE World_Notes ADD COLUMN gm_id INTEGER REFERENCES Users (id)"
            )
