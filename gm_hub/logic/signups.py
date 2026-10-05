"""Подсистема «Запись»: заявки Игроков на сессии (п. 4.2.3 ТЗ)."""

from gm_hub.config import now_str
from gm_hub.logic.auth import check_gm
from gm_hub.logic.errors import AccessError, ValidationError
from gm_hub.logic.games import free_seats, get_game

STATUS_NAMES = {
    "PENDING": "На рассмотрении",
    "CONFIRMED": "Подтверждена",
    "REJECTED": "Отклонена",
}

# Общая часть запроса: заявка + сессия + персонаж + игрок.
SIGNUPS_QUERY = """
    SELECT s.*, g.title AS game_title, g.scheduled_at,
        c.name AS character_name, c.class AS character_class,
        c.level AS character_level, u.full_name AS player_name
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

    with conn:
        cur = conn.execute(
            "INSERT INTO Game_Signups (game_id, character_id, status, comment, "
            "created_at) VALUES (?, ?, 'PENDING', ?, ?)",
            (game_id, character_id, comment.strip(), now_str()),
        )
    return cur.lastrowid


def withdraw_signup(conn, user, signup_id) -> None:
    """Отзывает (удаляет) свою заявку, пока она на рассмотрении.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Игрок).
        signup_id: id заявки.

    Raises:
        ValidationError: Если заявка уже рассмотрена или чужая.
    """
    signup = conn.execute(
        SIGNUPS_QUERY + " WHERE s.id = ? AND c.user_id = ?", (signup_id, user["id"])
    ).fetchone()
    if signup is None:
        raise ValidationError("Заявка", "Выберите свою заявку в таблице.")
    if signup["status"] != "PENDING":
        raise ValidationError("Заявка", "Отозвать можно только заявку на рассмотрении.")
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
        AccessError: Если пользователь не Мастер.
        ValidationError: Если мест нет или заявка уже рассмотрена.
    """
    check_gm(user)
    with conn:
        signup = conn.execute(
            "SELECT * FROM Game_Signups WHERE id = ?", (signup_id,)
        ).fetchone()
        if signup is None or signup["status"] != "PENDING":
            raise ValidationError("Заявка", "Подтвердить можно только новую заявку.")
        game = get_game(conn, signup["game_id"])
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


def reject_signup(conn, user, signup_id) -> None:
    """Отклоняет заявку.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер).
        signup_id: id заявки.

    Raises:
        AccessError: Если пользователь не Мастер.
        ValidationError: Если заявка уже отклонена.
    """
    check_gm(user)
    signup = conn.execute(
        "SELECT status FROM Game_Signups WHERE id = ?", (signup_id,)
    ).fetchone()
    if signup is None or signup["status"] == "REJECTED":
        raise ValidationError("Заявка", "Эта заявка уже отклонена.")
    with conn:
        conn.execute(
            "UPDATE Game_Signups SET status = 'REJECTED', decided_at = ? WHERE id = ?",
            (now_str(), signup_id),
        )
