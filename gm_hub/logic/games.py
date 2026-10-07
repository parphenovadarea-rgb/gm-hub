"""Подсистема «Расписание»: игровые сессии Мастера (п. 4.2.3 ТЗ)."""

from datetime import datetime

from gm_hub.config import DATETIME_FORMAT, SHOW_FORMAT, now_str
from gm_hub.logic.auth import check_gm
from gm_hub.logic.errors import AccessError, ValidationError, require

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


# Фильтр витрины по дате: подпись -> сколько дней вперёд (None — все даты).
PERIOD_DAYS = {"Все даты": None, "7 дней": 7, "30 дней": 30}


def in_period(scheduled_at: str, days, now: datetime | None = None) -> bool:
    """Проверяет, что сессия начнётся не позже чем через days дней.

    Args:
        scheduled_at: Дата сессии в формате БД «ГГГГ-ММ-ДД ЧЧ:ММ».
        days: Число дней вперёд или None — подходит любая дата.
        now: Текущий момент (для тестов), по умолчанию — сейчас.

    Returns:
        True, если сессия попадает в выбранный период.
    """
    if days is None:
        return True
    now = now or datetime.now()
    start = datetime.strptime(scheduled_at, DATETIME_FORMAT)
    return (start - now).total_seconds() <= days * 24 * 3600


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
        AccessError: Если пользователь не Мастер или сессия чужая.
        ValidationError: Если данные неверные.
    """
    check_gm(user)
    if game_id is not None:
        check_owner(conn, user, game_id)
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
    """Отменяет сессию; её заявки на рассмотрении автоматически отклоняются.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.

    Raises:
        AccessError: Если сессия чужая.
    """
    check_owner(conn, user, game_id)
    with conn:
        conn.execute("UPDATE Games SET status = 'CANCELLED' WHERE id = ?", (game_id,))
        # Новые заявки на отменённую сессию отклоняются, Игрок увидит причину.
        conn.execute(
            "UPDATE Game_Signups SET status = 'REJECTED', decided_at = ?, "
            "reason = 'Сессия отменена' WHERE game_id = ? AND status = 'PENDING'",
            (now_str(), game_id),
        )


def delete_game(conn, user, game_id) -> None:
    """Удаляет отменённую сессию вместе с её заявками и заметкой.

    Удалять можно только отменённую сессию, чтобы случайно не стереть
    запланированную игру с подтверждёнными игроками.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.

    Raises:
        AccessError: Если сессия чужая.
        ValidationError: Если сессия не отменена.
    """
    game = check_owner(conn, user, game_id)
    if game["status"] != "CANCELLED":
        raise ValidationError(
            "Сессия", "Удалить можно только отменённую сессию. Сначала отмените её."
        )
    with conn:
        conn.execute("DELETE FROM Game_Signups WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM Game_Notes WHERE game_id = ?", (game_id,))
        conn.execute("DELETE FROM Games WHERE id = ?", (game_id,))


def check_owner(conn, user, game_id):
    """Проверяет, что сессия принадлежит текущему Мастеру.

    У каждого Мастера свои сессии: чужие нельзя изменить, отменить,
    обработать по ним заявки или прочитать заметки.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.
        game_id: id сессии.

    Returns:
        Строка сессии.

    Raises:
        AccessError: Если пользователь не Мастер или сессия чужая.
        ValidationError: Если сессия не выбрана или не найдена.
    """
    check_gm(user)
    game = get_game(conn, game_id) if game_id is not None else None
    if game is None:
        raise ValidationError("Сессия", "Выберите сессию.")
    if game["gm_id"] != user["id"]:
        raise AccessError("Это сессия другого Мастера.")
    return game


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


def save_summary(conn, user, game_id, text) -> None:
    """Сохраняет итоги прошедшей сессии — их увидят Игроки в «Мои записи».

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        game_id: id сессии.
        text: Текст итогов.

    Raises:
        AccessError: Если сессия чужая.
        ValidationError: Если сессия ещё не прошла.
    """
    game = check_owner(conn, user, game_id)
    if game["status"] != "CLOSED":
        raise ValidationError(
            "Итоги", "Итоги можно написать только к прошедшей сессии."
        )
    with conn:
        conn.execute(
            "UPDATE Games SET summary = ? WHERE id = ?",
            (text.strip() or None, game_id),
        )


def master_stats(conn, user) -> dict:
    """Считает статистику Мастера для вкладки «Статистика».

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).

    Returns:
        Словарь: planned, closed, cancelled — число сессий по статусам;
        fill — средняя заполняемость прошедших сессий в процентах (или None);
        players — до 5 самых активных Игроков: (ФИО, подтверждённых заявок).
    """
    check_gm(user)
    closed = list_games(conn, "CLOSED", user["id"])
    stats = {
        "planned": len(list_games(conn, "PLANNED", user["id"])),
        "closed": len(closed),
        "cancelled": len(list_games(conn, "CANCELLED", user["id"])),
        "fill": None,
    }
    if closed:
        percents = [g["confirmed"] * 100 / g["max_players"] for g in closed]
        stats["fill"] = round(sum(percents) / len(percents))
    stats["players"] = [
        (row["full_name"], row["games"])
        for row in conn.execute(
            "SELECT u.full_name, COUNT(*) AS games FROM Game_Signups s "
            "JOIN Games g ON g.id = s.game_id "
            "JOIN Characters c ON c.id = s.character_id "
            "JOIN Users u ON u.id = c.user_id "
            "WHERE g.gm_id = ? AND g.status != 'CANCELLED' "
            "AND s.status = 'CONFIRMED' "
            "GROUP BY u.id ORDER BY games DESC, u.full_name LIMIT 5",
            (user["id"],),
        )
    ]
    return stats


def get_game(conn, game_id):
    """Возвращает одну сессию с числом заявок.

    Args:
        conn: Подключение к БД.
        game_id: id сессии.

    Returns:
        Строка с полями сессии, confirmed и pending, или None.
    """
    return conn.execute(GAMES_QUERY + " WHERE g.id = ?", (game_id,)).fetchone()


def list_games(conn, status: str = "PLANNED", gm_id=None):
    """Возвращает сессии одного Мастера с нужным статусом, по дате.

    Для статуса PLANNED это и расписание Мастера, и витрина Игрока
    (Игрок видит сессии выбранного Мастера).

    Args:
        conn: Подключение к БД.
        status: PLANNED, CLOSED или CANCELLED.
        gm_id: id Мастера. None — сессии всех Мастеров.

    Returns:
        Список строк с полями сессии, confirmed и pending.
    """
    close_past_games(conn)
    sql = GAMES_QUERY + " WHERE g.status = ?"
    params = [status]
    if gm_id is not None:
        sql += " AND g.gm_id = ?"
        params.append(gm_id)
    return conn.execute(sql + " ORDER BY g.scheduled_at", params).fetchall()
