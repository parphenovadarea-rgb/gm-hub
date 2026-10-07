"""Подсистема «Сюжетный блокнот»: заметки к сессиям и база мира (п. 4.2.4 ТЗ).

Все функции сначала проверяют роль: Игрок не получает заметки даже
при прямом вызове (п. 4.1.9 ТЗ). У каждого Мастера свой блокнот и своя
база мира — чужие записи не видны.
"""

from gm_hub.config import now_str
from gm_hub.logic.auth import check_gm
from gm_hub.logic.errors import AccessError, ValidationError, require
from gm_hub.logic.games import check_owner

CATEGORY_NAMES = {"LORE": "Лор", "NPC": "NPC", "LOCATION": "Локации"}


def get_game_note(conn, user, game_id):
    """Возвращает заметку к своей сессии.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.

    Returns:
        Строка таблицы Game_Notes или None, если заметки ещё нет.

    Raises:
        AccessError: Если пользователь не Мастер или сессия чужая.
    """
    check_owner(conn, user, game_id)
    return conn.execute(
        "SELECT * FROM Game_Notes WHERE game_id = ?", (game_id,)
    ).fetchone()


def save_game_note(conn, user, game_id, content) -> str:
    """Сохраняет заметку к своей сессии и фиксирует время изменения.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.
        content: Текст заметки.

    Returns:
        Время сохранения в формате БД.
    """
    if game_id is None:
        raise ValidationError("Сессия", "Выберите сессию в списке слева.")
    note = get_game_note(conn, user, game_id)
    updated_at = now_str()
    with conn:
        if note is None:
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
    """Удаляет заметку к своей сессии.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.
    """
    if game_id is None:
        raise ValidationError("Сессия", "Выберите сессию в списке слева.")
    check_owner(conn, user, game_id)
    with conn:
        conn.execute("DELETE FROM Game_Notes WHERE game_id = ?", (game_id,))


def search_game_notes(conn, user, query: str) -> set:
    """Ищет сессии Мастера, в заметке или названии которых есть текст.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        query: Искомый текст (без учёта регистра).

    Returns:
        Множество id подходящих сессий.
    """
    check_gm(user)
    rows = conn.execute(
        "SELECT g.id, g.title, n.content FROM Games g "
        "LEFT JOIN Game_Notes n ON n.game_id = g.id WHERE g.gm_id = ?",
        (user["id"],),
    ).fetchall()
    # LIKE в SQLite не понимает регистр русских букв, поэтому ищем в Python.
    query = query.strip().lower()
    return {
        row["id"]
        for row in rows
        if query in row["title"].lower() or query in (row["content"] or "").lower()
    }


def list_world_notes(conn, user, category=None, search=""):
    """Возвращает записи базы мира текущего Мастера.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        category: LORE, NPC, LOCATION или None — все категории.
        search: Часть заголовка для поиска (без учёта регистра).

    Returns:
        Список строк таблицы World_Notes.
    """
    check_gm(user)
    sql = "SELECT * FROM World_Notes WHERE gm_id = ?"
    params = [user["id"]]
    if category:
        sql += " AND category = ?"
        params.append(category)
    rows = conn.execute(sql + " ORDER BY category, title", params).fetchall()
    # LIKE в SQLite не понимает регистр русских букв, поэтому ищем в Python.
    search = search.strip().lower()
    return [row for row in rows if search in row["title"].lower()]


def get_world_note(conn, user, note_id):
    """Возвращает свою запись базы мира.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        note_id: id записи.

    Returns:
        Строка таблицы World_Notes.

    Raises:
        AccessError: Если запись принадлежит другому Мастеру.
    """
    check_gm(user)
    note = conn.execute("SELECT * FROM World_Notes WHERE id = ?", (note_id,)).fetchone()
    if note is None or note["gm_id"] != user["id"]:
        raise AccessError("Это запись другого Мастера.")
    return note


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
    if note_id is not None:
        get_world_note(conn, user, note_id)
    with conn:
        if note_id is None:
            cur = conn.execute(
                "INSERT INTO World_Notes (gm_id, category, title, content, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (user["id"], category, title, content, now_str()),
            )
            return cur.lastrowid
        conn.execute(
            "UPDATE World_Notes SET category = ?, title = ?, content = ?, "
            "updated_at = ? WHERE id = ?",
            (category, title, content, now_str(), note_id),
        )
    return note_id


def delete_world_note(conn, user, note_id) -> None:
    """Удаляет свою запись базы мира.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        note_id: id записи.
    """
    get_world_note(conn, user, note_id)
    with conn:
        conn.execute("DELETE FROM World_Notes WHERE id = ?", (note_id,))
