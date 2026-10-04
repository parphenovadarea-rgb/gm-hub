"""Подсистема «Расписание»: игровые сессии Мастера (п. 4.2.3 ТЗ)."""

from datetime import datetime

from gm_hub.config import DATETIME_FORMAT, SHOW_FORMAT, now_str
from gm_hub.logic.auth import check_gm
from gm_hub.logic.errors import ValidationError, require

STATUS_NAMES = {"PLANNED": "Запланирована", "CLOSED": "Прошла", "CANCELLED": "Отменена"}

# Общая часть запроса: сессия + число подтверждённых и новых заявок.
GAMES_QUERY = """
    SELECT g.*, u.full_name AS gm_name,
        (SELECT COUNT(*) FROM Game_Signups s
         WHERE s.game_id = g.id AND s.status = 'CONFIRMED') AS confirmed,
        (SELECT COUNT(*) FROM Game_Signups s
         WHERE s.game_id = g.id AND s.status = 'PENDING') AS pending
    FROM Games g JOIN Users u ON u.id = g.gm_id
"""


def free_seats(max_players: int, confirmed: int) -> int:
    """Считает свободные места по формуле F = M − C (п. 4.3.1 ТЗ).

    Args:
        max_players: M — лимит мест сессии.
        confirmed: C — число подтверждённых заявок.

    Returns:
        Число свободных мест F.
    """
    return max_players - confirmed


def parse_datetime(date_text: str, time_text: str) -> str:
    """Проверяет дату и время из формы и переводит их в формат БД.

    Args:
        date_text: Дата «ДД.ММ.ГГГГ».
        time_text: Время «ЧЧ:ММ».

    Returns:
        Дата и время в формате БД.

    Raises:
        ValidationError: Если формат неверный или дата уже прошла.
    """
    date_text = require(date_text, "Дата")
    time_text = require(time_text, "Время")
    try:
        when = datetime.strptime(f"{date_text} {time_text}", SHOW_FORMAT)
    except ValueError:
        raise ValidationError("Дата", "Введите дату как ДД.ММ.ГГГГ, а время как ЧЧ:ММ.")
    if when < datetime.now():
        raise ValidationError(
            "Дата", f"Дата {date_text} {time_text} уже прошла. Укажите будущую дату."
        )
    return when.strftime(DATETIME_FORMAT)


def check_max_players(value) -> int:
    """Проверяет лимит мест (п. 4.1.4 ТЗ).

    Args:
        value: Введённое значение.

    Returns:
        Лимит мест числом.

    Raises:
        ValidationError: Если это не целое число больше нуля.
    """
    try:
        value = int(str(value).strip())
    except ValueError:
        raise ValidationError("Лимит мест", "Лимит мест должен быть целым числом.")
    if value <= 0:
        raise ValidationError("Лимит мест", "Лимит мест должен быть больше нуля.")
    return value


def save_game(
    conn, user, title, description, date_text, time_text, max_players, game_id=None
):
    """Создаёт новую сессию или изменяет существующую.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        title: Название сессии.
        description: Описание для игроков.
        date_text: Дата «ДД.ММ.ГГГГ».
        time_text: Время «ЧЧ:ММ».
        max_players: Лимит мест.
        game_id: id сессии для изменения, None — новая сессия.

    Returns:
        id сессии.

    Raises:
        AccessError: Если пользователь не Мастер.
        ValidationError: Если данные неверные.
    """
    check_gm(user)
    title = require(title, "Название")
    scheduled_at = parse_datetime(date_text, time_text)
    max_players = check_max_players(max_players)
    with conn:
        if game_id is None:
            cur = conn.execute(
                "INSERT INTO Games (gm_id, title, description, scheduled_at, "
                "max_players, status) VALUES (?, ?, ?, ?, ?, 'PLANNED')",
                (user["id"], title, description.strip(), scheduled_at, max_players),
            )
            return cur.lastrowid
        confirmed = get_game(conn, game_id)["confirmed"]
        if max_players < confirmed:
            raise ValidationError(
                "Лимит мест",
                f"Уже подтверждено {confirmed} заявок, лимит не может быть меньше.",
            )
        conn.execute(
            "UPDATE Games SET title = ?, description = ?, scheduled_at = ?, "
            "max_players = ? WHERE id = ?",
            (title, description.strip(), scheduled_at, max_players, game_id),
        )
    return game_id


def cancel_game(conn, user, game_id) -> None:
    """Отменяет сессию.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.
    """
    check_gm(user)
    with conn:
        conn.execute("UPDATE Games SET status = 'CANCELLED' WHERE id = ?", (game_id,))


def delete_game(conn, user, game_id) -> None:
    """Удаляет отменённую сессию вместе с её заявками и заметкой.

    Удалять можно только отменённую сессию, чтобы случайно не стереть
    запланированную игру с подтверждёнными игроками.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.

    Raises:
        AccessError: Если пользователь не Мастер.
        ValidationError: Если сессия не отменена.
    """
    check_gm(user)
    game = get_game(conn, game_id)
    if game is None or game["status"] != "CANCELLED":
        raise ValidationError(
            "Сессия", "Удалить можно только отменённую сессию. Сначала отмените её."
        )
    with conn:
        conn.execute("DELETE FROM Game_Signups WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM Game_Notes WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM Games WHERE id = ?", (game_id,))


def close_past_games(conn) -> None:
    """Помечает прошедшие запланированные сессии статусом CLOSED.

    Args:
        conn: Подключение к БД.
    """
    with conn:
        conn.execute(
            "UPDATE Games SET status = 'CLOSED' "
            "WHERE status = 'PLANNED' AND scheduled_at < ?",
            (now_str(),),
        )


def get_game(conn, game_id):
    """Возвращает одну сессию с числом заявок.

    Args:
        conn: Подключение к БД.
        game_id: id сессии.

    Returns:
        Строка с полями сессии, confirmed и pending, или None.
    """
    return conn.execute(GAMES_QUERY + " WHERE g.id = ?", (game_id,)).fetchone()


def list_games(conn, status: str = "PLANNED"):
    """Возвращает сессии с нужным статусом, отсортированные по дате.

    Для статуса PLANNED это и расписание Мастера, и витрина Игрока.

    Args:
        conn: Подключение к БД.
        status: PLANNED, CLOSED или CANCELLED.

    Returns:
        Список строк с полями сессии, confirmed и pending.
    """
    close_past_games(conn)
    return conn.execute(
        GAMES_QUERY + " WHERE g.status = ? ORDER BY g.scheduled_at", (status,)
    ).fetchall()
