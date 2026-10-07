"""Подсистема «Персонажи»: карточки персонажей Игрока (п. 4.2.2 ТЗ)."""

from gm_hub.logic.errors import AccessError, ValidationError, require
from gm_hub.logic.games import check_owner

# Справочные значения по SRD 5.1 (п. 4.1.12 ТЗ). В поле можно ввести и своё.
RACES = "Человек Эльф Дварф Полурослик Гном Полуорк Тифлинг".split()
CLASSES = (
    "Варвар Бард Жрец Друид Воин Монах Паладин Следопыт Плут Чародей Колдун Волшебник"
).split()


def list_characters(conn, user):
    """Возвращает персонажей текущего Игрока.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.

    Returns:
        Список строк таблицы Characters.
    """
    return conn.execute(
        "SELECT * FROM Characters WHERE user_id = ? ORDER BY name", (user["id"],)
    ).fetchall()


def get_character(conn, character_id):
    """Возвращает карточку персонажа вместе с ФИО владельца.

    Args:
        conn: Подключение к БД.
        character_id: id персонажа.

    Returns:
        Строка с полями персонажа и owner_name или None.
    """
    return conn.execute(
        "SELECT c.*, u.full_name AS owner_name FROM Characters c "
        "JOIN Users u ON u.id = c.user_id WHERE c.id = ?",
        (character_id,),
    ).fetchone()


def check_level(level) -> int:
    """Проверяет уровень персонажа.

    Args:
        level: Введённое значение.

    Returns:
        Уровень числом.

    Raises:
        ValidationError: Если это не целое число от 1 до 20.
    """
    try:
        level = int(str(level).strip())
    except ValueError:
        raise ValidationError("Уровень", "Уровень должен быть целым числом.")
    if not 1 <= level <= 20:
        raise ValidationError("Уровень", "Уровень должен быть от 1 до 20.")
    return level


def save_character(conn, user, name, race, cls, level, backstory, character_id=None):
    """Создаёт нового персонажа или изменяет существующего.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Игрок).
        name: Имя персонажа.
        race: Раса.
        cls: Класс.
        level: Уровень от 1 до 20.
        backstory: Предыстория.
        character_id: id персонажа для изменения, None — новый персонаж.

    Returns:
        id персонажа.

    Raises:
        ValidationError: Если имя пустое или уровень неверный.
    """
    name = require(name, "Имя")
    level = check_level(level)
    data = (name, race.strip(), cls.strip(), level, backstory.strip())
    with conn:
        if character_id is None:
            cur = conn.execute(
                "INSERT INTO Characters (name, race, class, level, backstory, user_id)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                data + (user["id"],),
            )
            return cur.lastrowid
        conn.execute(
            "UPDATE Characters SET name = ?, race = ?, class = ?, level = ?, "
            "backstory = ? WHERE id = ? AND user_id = ?",
            data + (character_id, user["id"]),
        )
    return character_id


def active_signups(conn, character_id):
    """Возвращает заявки персонажа со статусом PENDING или CONFIRMED.

    Учитываются только запланированные сессии: заявки на отменённую
    или уже прошедшую сессию удаление персонажа не блокируют.

    Args:
        conn: Подключение к БД.
        character_id: id персонажа.

    Returns:
        Список строк с названием сессии и статусом заявки.
    """
    return conn.execute(
        "SELECT g.title, s.status FROM Game_Signups s "
        "JOIN Games g ON g.id = s.game_id "
        "WHERE s.character_id = ? AND s.status IN ('PENDING', 'CONFIRMED') "
        "AND g.status = 'PLANNED'",
        (character_id,),
    ).fetchall()


def delete_character(conn, user, character_id) -> None:
    """Удаляет персонажа, если у него нет активных заявок (п. 4.1.4 ТЗ).

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.
        character_id: id персонажа.

    Raises:
        AccessError: Если персонаж чужой.
        ValidationError: Если у персонажа есть активные заявки.
    """
    character = get_character(conn, character_id)
    if character is None or character["user_id"] != user["id"]:
        raise AccessError("Можно удалять только своих персонажей.")
    active = active_signups(conn, character_id)
    if active:
        titles = ", ".join(f"«{row['title']}»" for row in active)
        raise ValidationError(
            "Персонаж",
            f"Персонажа «{character['name']}» удалить нельзя: "
            f"у него есть активные заявки ({titles}).",
        )
    with conn:
        # Отклонённые заявки удаляем вместе с персонажем, иначе мешает внешний ключ.
        conn.execute("DELETE FROM Game_Signups WHERE character_id = ?", (character_id,))
        conn.execute("DELETE FROM Characters WHERE id = ?", (character_id,))


def level_up_after_game(conn, user, game_id) -> int:
    """Повышает на 1 уровень всех подтверждённых участников прошедшей сессии.

    Повысить уровни за одну сессию можно только один раз; уровень не
    поднимается выше 20.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь (Мастер — владелец сессии).
        game_id: id сессии.

    Returns:
        Число персонажей, получивших новый уровень.

    Raises:
        AccessError: Если сессия чужая.
        ValidationError: Если сессия не прошла или уровни уже повышены.
    """
    game = check_owner(conn, user, game_id)
    if game["status"] != "CLOSED":
        raise ValidationError(
            "Уровни", "Повысить уровни можно только после прошедшей сессии."
        )
    if game["levels_given"]:
        raise ValidationError("Уровни", "За эту сессию уровни уже повышены.")
    with conn:
        cur = conn.execute(
            "UPDATE Characters SET level = level + 1 WHERE level < 20 AND id IN "
            "(SELECT character_id FROM Game_Signups "
            "WHERE game_id = ? AND status = 'CONFIRMED')",
            (game_id,),
        )
        conn.execute("UPDATE Games SET levels_given = 1 WHERE id = ?", (game_id,))
    return cur.rowcount
