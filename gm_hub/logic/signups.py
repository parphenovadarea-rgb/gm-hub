"""Подсистема «Запись»: заявки Игроков на сессии (п. 4.2.3 ТЗ)."""

import csv

from gm_hub.config import now_str, to_show
from gm_hub.logic.auth import check_gm
from gm_hub.logic.errors import AccessError, ValidationError
from gm_hub.logic.games import check_owner, free_seats, get_game

STATUS_NAMES = {
    "PENDING": "На рассмотрении",
    "CONFIRMED": "Подтверждена",
    "REJECTED": "Отклонена",
}

# Общая часть запроса: заявка + сессия + персонаж + игрок.
SIGNUPS_QUERY = """
    SELECT s.*, g.title AS game_title, g.scheduled_at, g.status AS game_status,
        c.name AS character_name, c.class AS character_class,
        c.level AS character_level, u.full_name AS player_name,
        (SELECT full_name FROM Users WHERE id = g.gm_id) AS gm_name
    FROM Game_Signups s
    JOIN Games g ON g.id = s.game_id
    JOIN Characters c ON c.id = s.character_id
    JOIN Users u ON u.id = c.user_id
"""


def create_signup(conn, user, game_id, character_id, comment="") -> int:
    """Подаёт заявку на сессию от имени персонажа Игрока.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Игрок).
        game_id: id сессии.
        character_id: id выбранного персонажа или None.
        comment: Необязательный комментарий Мастеру.

    Returns:
        id новой заявки.

    Raises:
        ValidationError: Если персонаж не выбран, сессия недоступна
            или такая заявка уже есть.
    """
    if game_id is None:
        raise ValidationError("Сессия", "Выберите сессию в таблице.")
    if character_id is None:
        raise ValidationError("Персонаж", "Выберите персонажа для заявки.")

    character = conn.execute(
        "SELECT user_id FROM Characters WHERE id = ?", (character_id,)
    ).fetchone()
    if character is None or character["user_id"] != user["id"]:
        raise AccessError("Заявку можно подать только своим персонажем.")

    game = get_game(conn, game_id)
    if game is None or game["status"] != "PLANNED":
        raise ValidationError("Сессия", "На эту сессию запись закрыта.")

    double = conn.execute(
        "SELECT id FROM Game_Signups WHERE game_id = ? AND character_id = ?",
        (game_id, character_id),
    ).fetchone()
    if double:
        raise ValidationError(
            "Персонаж", "Этот персонаж уже подавал заявку на эту сессию."
        )

    # один Игрок — одна активная заявка на сессию, даже с разными персонажами
    active = player_signup(conn, game_id, user["id"], ("PENDING", "CONFIRMED"))
    if active:
        raise ValidationError(
            "Персонаж",
            f"У вас уже есть заявка на эту сессию (персонаж "
            f"{active['character_name']}). Чтобы записаться другим персонажем, "
            "сначала отзовите её в разделе «Мои записи».",
        )

    with conn:
        cur = conn.execute(
            "INSERT INTO Game_Signups (game_id, character_id, status, comment, "
            "created_at) VALUES (?, ?, 'PENDING', ?, ?)",
            (game_id, character_id, comment.strip(), now_str()),
        )
    return cur.lastrowid


def player_signup(conn, game_id, player_id, statuses):
    """Ищет заявку Игрока на сессию с одним из указанных статусов.

    Args:
        conn: Подключение к БД.
        game_id: id сессии.
        player_id: id Игрока (владельца персонажей).
        statuses: Подходящие статусы, например ("CONFIRMED",).

    Returns:
        Строка заявки (с именем персонажа) или None.
    """
    marks = ", ".join("?" * len(statuses))
    return conn.execute(
        SIGNUPS_QUERY
        + f" WHERE s.game_id = ? AND c.user_id = ? AND s.status IN ({marks})",
        (game_id, player_id, *statuses),
    ).fetchone()


def withdraw_signup(conn, user, signup_id) -> None:
    """Отзывает (удаляет) свою заявку — на рассмотрении или подтверждённую.

    Подтверждённую заявку тоже можно отозвать, если Игрок не сможет прийти:
    место освобождается для следующей заявки.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Игрок).
        signup_id: id заявки.

    Raises:
        ValidationError: Если заявка отклонена, сессия уже не запланирована
            или заявка чужая.
    """
    signup = conn.execute(
        SIGNUPS_QUERY + " WHERE s.id = ? AND c.user_id = ?", (signup_id, user["id"])
    ).fetchone()
    if signup is None:
        raise ValidationError("Заявка", "Выберите свою заявку в таблице.")
    if signup["status"] == "REJECTED" or signup["game_status"] != "PLANNED":
        raise ValidationError(
            "Заявка", "Отозвать можно только активную заявку на предстоящую сессию."
        )
    with conn:
        conn.execute("DELETE FROM Game_Signups WHERE id = ?", (signup_id,))


def list_for_player(conn, user):
    """Возвращает заявки только текущего Игрока (сценарий 14 п. 6.1 ТЗ).

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.

    Returns:
        Список строк заявок, отсортированных по дате сессии.
    """
    return conn.execute(
        SIGNUPS_QUERY + " WHERE c.user_id = ? ORDER BY g.scheduled_at", (user["id"],)
    ).fetchall()


def list_for_game(conn, game_id):
    """Возвращает все заявки на сессию для Мастера.

    Args:
        conn: Подключение к БД.
        game_id: id сессии.

    Returns:
        Список строк заявок, новые сверху.
    """
    return conn.execute(
        SIGNUPS_QUERY + " WHERE s.game_id = ? ORDER BY s.created_at DESC", (game_id,)
    ).fetchall()


def confirm_signup(conn, user, signup_id) -> None:
    """Подтверждает заявку, если есть свободные места (п. 4.3.1 ТЗ).

    Проверка C < M и смена статуса выполняются в одной транзакции.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        signup_id: id заявки.

    Raises:
        AccessError: Если пользователь не Мастер или сессия чужая.
        ValidationError: Если мест нет или заявка уже рассмотрена.
    """
    check_gm(user)
    with conn:
        signup = conn.execute(
            "SELECT * FROM Game_Signups WHERE id = ?", (signup_id,)
        ).fetchone()
        if signup is None or signup["status"] != "PENDING":
            raise ValidationError("Заявка", "Подтвердить можно только новую заявку.")
        game = check_owner(conn, user, signup["game_id"])
        player_id = conn.execute(
            "SELECT user_id FROM Characters WHERE id = ?", (signup["character_id"],)
        ).fetchone()["user_id"]
        other = player_signup(conn, signup["game_id"], player_id, ("CONFIRMED",))
        if other:
            raise ValidationError(
                "Заявка",
                f"Подтвердить нельзя: у игрока {other['player_name']} уже "
                f"подтверждена заявка на эту сессию (персонаж "
                f"{other['character_name']}). Один игрок — один персонаж в сессии.",
            )
        if free_seats(game["max_players"], game["confirmed"]) <= 0:
            raise ValidationError(
                "Заявка",
                f"Подтвердить нельзя: на «{game['title']}» уже подтверждено "
                f"{game['confirmed']} заявок из {game['max_players']}. "
                "Отклоните заявку или увеличьте лимит мест.",
            )
        conn.execute(
            "UPDATE Game_Signups SET status = 'CONFIRMED', decided_at = ? WHERE id = ?",
            (now_str(), signup_id),
        )


def reject_signup(conn, user, signup_id, reason: str = "") -> None:
    """Отклоняет заявку и запоминает причину отказа.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        signup_id: id заявки.
        reason: Причина отказа (необязательно), её увидит Игрок.

    Raises:
        AccessError: Если пользователь не Мастер или сессия чужая.
        ValidationError: Если заявка уже отклонена.
    """
    check_gm(user)
    signup = conn.execute(
        "SELECT status, game_id FROM Game_Signups WHERE id = ?", (signup_id,)
    ).fetchone()
    if signup is not None:
        check_owner(conn, user, signup["game_id"])
    if signup is None or signup["status"] == "REJECTED":
        raise ValidationError("Заявка", "Эта заявка уже отклонена.")
    with conn:
        conn.execute(
            "UPDATE Game_Signups SET status = 'REJECTED', decided_at = ?, reason = ? "
            "WHERE id = ?",
            (now_str(), reason.strip() or None, signup_id),
        )


def seen_at(conn, user):
    """Возвращает, когда Игрок последний раз открывал «Мои записи» (или None)."""
    row = conn.execute(
        "SELECT signups_seen_at FROM Users WHERE id = ?", (user["id"],)
    ).fetchone()
    return row["signups_seen_at"] if row else None


def count_new_decisions(conn, user) -> int:
    """Считает решения Мастеров по заявкам Игрока, которые он ещё не видел.

    Новое решение — заявка подтверждена или отклонена позже, чем Игрок
    последний раз открывал раздел «Мои записи».

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Игрок).

    Returns:
        Число новых решений.
    """
    seen = seen_at(conn, user) or ""
    return conn.execute(
        "SELECT COUNT(*) FROM Game_Signups s "
        "JOIN Characters c ON c.id = s.character_id "
        "WHERE c.user_id = ? AND s.decided_at IS NOT NULL AND s.decided_at > ?",
        (user["id"], seen),
    ).fetchone()[0]


def mark_decisions_seen(conn, user) -> None:
    """Запоминает, что Игрок просмотрел решения по своим заявкам.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Игрок).
    """
    with conn:
        conn.execute(
            "UPDATE Users SET signups_seen_at = ? WHERE id = ?",
            (now_str(), user["id"]),
        )


def export_participants(conn, user, game_id, path) -> int:
    """Сохраняет список подтверждённых участников сессии в файл CSV.

    Файл открывается в Excel: разделитель «;», кодировка UTF-8 с меткой BOM.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер — владелец сессии).
        game_id: id сессии.
        path: Путь к файлу .csv.

    Returns:
        Число участников в файле.

    Raises:
        AccessError: Если пользователь не Мастер или сессия чужая.
    """
    check_gm(user)
    game = check_owner(conn, user, game_id)
    rows = conn.execute(
        "SELECT c.name, c.race, c.class, c.level, u.full_name, s.comment "
        "FROM Game_Signups s "
        "JOIN Characters c ON c.id = s.character_id "
        "JOIN Users u ON u.id = c.user_id "
        "WHERE s.game_id = ? AND s.status = 'CONFIRMED' ORDER BY c.name",
        (game_id,),
    ).fetchall()
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([f"Сессия: {game['title']}", to_show(game["scheduled_at"])])
        writer.writerow(
            ["Персонаж", "Раса", "Класс", "Уровень", "Игрок", "Комментарий"]
        )
        for row in rows:
            writer.writerow([value if value is not None else "" for value in row])
    return len(rows)
