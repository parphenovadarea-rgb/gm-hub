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
    # В БД, созданной более ранней версией программы, может не быть новых
    # столбцов — добавляем их, чтобы старый файл БД продолжил работать.
    add_column(conn, "World_Notes", "gm_id", "INTEGER REFERENCES Users (id)")
    add_column(conn, "Game_Signups", "reason", "TEXT")
    add_column(conn, "Users", "signups_seen_at", "TEXT")
    add_column(conn, "Games", "summary", "TEXT")
    add_column(conn, "Games", "levels_given", "INTEGER NOT NULL DEFAULT 0")


def add_column(conn: sqlite3.Connection, table: str, column: str, sql_type: str):
    """Добавляет столбец в таблицу, если его ещё нет.

    Args:
        conn: Подключение к БД.
        table: Имя таблицы (только из кода программы, не от пользователя).
        column: Имя столбца.
        sql_type: Тип столбца, например «TEXT».
    """
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in columns:
        with conn:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
