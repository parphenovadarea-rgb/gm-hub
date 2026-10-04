"""Подсистема «Сюжетный блокнот»: заметки к сессиям и база мира (п. 4.2.4 ТЗ).

Все функции сначала проверяют роль: Игрок не получает заметки даже
при прямом вызове (п. 4.1.9 ТЗ).
"""

from gm_hub.config import now_str
from gm_hub.logic.auth import check_gm
from gm_hub.logic.errors import ValidationError, require

CATEGORY_NAMES = {"LORE": "Лор", "NPC": "NPC", "LOCATION": "Локации"}


def get_game_note(conn, user, game_id):
    """Возвращает заметку к сессии.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.

    Returns:
        Строка таблицы Game_Notes или None, если заметки ещё нет.
    """
    check_gm(user)
    return conn.execute(
        "SELECT * FROM Game_Notes WHERE game_id = ?", (game_id,)
    ).fetchone()


def save_game_note(conn, user, game_id, content) -> str:
    """Сохраняет заметку к сессии и фиксирует время изменения.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.
        content: Текст заметки.

    Returns:
        Время сохранения в формате БД.
    """
    check_gm(user)
    if game_id is None:
        raise ValidationError("Сессия", "Выберите сессию в списке слева.")
    updated_at = now_str()
    with conn:
        if get_game_note(conn, user, game_id) is None:
            conn.execute(
                "INSERT INTO Game_Notes (game_id, content, updated_at) "
                "VALUES (?, ?, ?)",
                (game_id, content, updated_at),
            )
        else:
            conn.execute(
                "UPDATE Game_Notes SET content = ?, updated_at = ? WHERE game_id = ?",
                (content, updated_at, game_id),
            )
    return updated_at


def delete_game_note(conn, user, game_id) -> None:
    """Удаляет заметку к сессии.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.
    """
    check_gm(user)
    if game_id is None:
        raise ValidationError("Сессия", "Выберите сессию в списке слева.")
    with conn:
        conn.execute("DELETE FROM Game_Notes WHERE game_id = ?", (game_id,))


def list_world_notes(conn, user, category=None, search=""):
    """Возвращает записи базы мира.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        category: LORE, NPC, LOCATION или None — все категории.
        search: Часть заголовка для поиска.

    Returns:
        Список строк таблицы World_Notes.
    """
    check_gm(user)
    sql = "SELECT * FROM World_Notes WHERE title LIKE ?"
    params = [f"%{search.strip()}%"]
    if category:
        sql += " AND category = ?"
        params.append(category)
    return conn.execute(sql + " ORDER BY category, title", params).fetchall()


def save_world_note(conn, user, category, title, content, note_id=None) -> int:
    """Создаёт или изменяет запись базы мира.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        category: LORE, NPC или LOCATION.
        title: Заголовок.
        content: Текст записи.
        note_id: id записи для изменения, None — новая запись.

    Returns:
        id записи.

    Raises:
        ValidationError: Если заголовок пуст или категория не выбрана.
    """
    check_gm(user)
    if category not in CATEGORY_NAMES:
        raise ValidationError("Категория", "Выберите категорию.")
    title = require(title, "Заголовок")
    with conn:
        if note_id is None:
            cur = conn.execute(
                "INSERT INTO World_Notes (category, title, content, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (category, title, content, now_str()),
            )
            return cur.lastrowid
        conn.execute(
            "UPDATE World_Notes SET category = ?, title = ?, content = ?, "
            "updated_at = ? WHERE id = ?",
            (category, title, content, now_str(), note_id),
        )
    return note_id


def delete_world_note(conn, user, note_id) -> None:
    """Удаляет запись базы мира.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        note_id: id записи.
    """
    check_gm(user)
    with conn:
        conn.execute("DELETE FROM World_Notes WHERE id = ?", (note_id,))
