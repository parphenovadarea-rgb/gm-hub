"""Создаёт демонстрационную БД с данными из макетов: python seed.py.

Внимание: старый файл gm_hub.db удаляется.
"""

from datetime import datetime, timedelta

from gm_hub.config import DB_PATH
from gm_hub.db.database import connect, init_db
from gm_hub.logic import auth, characters, games, notes, signups


def in_days(days: int, time: str = "18:00") -> tuple[str, str]:
    """Возвращает дату через days дней в формате формы.

    Args:
        days: Через сколько дней.
        time: Время «ЧЧ:ММ».

    Returns:
        Пара (дата, время).
    """
    return (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y"), time


def main() -> None:
    """Заполняет БД пользователями, персонажами, сессиями, заявками и заметками."""
    DB_PATH.unlink(missing_ok=True)
    conn = connect()
    init_db(conn)

    # Пароль у всех демо-пользователей: 1234
    users = [
        ("Ильин Максим Сергеевич", "master", "GM"),
        ("Денисов Глеб Андреевич", "gleb", "PLAYER"),
        ("Соколов Артём Игоревич", "artem", "PLAYER"),
        ("Кравцова Елена Павловна", "elena", "PLAYER"),
        ("Жукова Полина Олеговна", "polina", "PLAYER"),
    ]
    for full_name, login, role in users:
        auth.register(conn, full_name, login, "1234", "1234", role)
    gm = auth.login_user(conn, "master", "1234")
    gleb = auth.login_user(conn, "gleb", "1234")
    artem = auth.login_user(conn, "artem", "1234")
    elena = auth.login_user(conn, "elena", "1234")
    polina = auth.login_user(conn, "polina", "1234")

    pip = characters.save_character(
        conn,
        gleb,
        "Пип",
        "Полурослик",
        "Плут",
        4,
        "Вырос в Сером Броде, в семье пекаря. Должен услугу гильдии картографов.",
    )
    corvin = characters.save_character(
        conn, gleb, "Корвин", "Человек", "Волшебник", 2, "Ученик городского мага."
    )
    torbek = characters.save_character(
        conn, artem, "Торбек", "Дварф", "Жрец", 4, "Ищет пропавшего брата."
    )
    eilin = characters.save_character(
        conn, elena, "Эйлин", "Эльф", "Следопыт", 4, "Проводник по горным тропам."
    )
    seira = characters.save_character(
        conn,
        polina,
        "Сэйра",
        "Человек",
        "Паладин",
        1,
        "Послушница храма Солнца, ищет того, кто устроил пожар в обители.",
    )

    fog = games.save_game(
        conn,
        gm,
        "Туман над Серым Бродом",
        "Расследование в портовом городе, 3–4 уровень",
        *in_days(2, "19:00"),
        4,
    )
    mine = games.save_game(
        conn,
        gm,
        "Шахта Эхо, ч. 3",
        "Спуск на нижние ярусы, 4 уровень",
        *in_days(5),
        3,
    )
    games.save_game(
        conn,
        gm,
        "Ваншот: ограбление храма Солнца",
        "Одна встреча на 4 часа, 1–3 уровень, новичкам можно",
        *in_days(12, "16:00"),
        4,
    )

    s1 = signups.create_signup(conn, gleb, mine, pip, "Приду к 18:15")
    s2 = signups.create_signup(conn, artem, mine, torbek)
    s3 = signups.create_signup(conn, elena, mine, eilin)
    s4 = signups.create_signup(conn, gleb, mine, corvin, "Если Пип не пройдёт")
    signups.create_signup(conn, polina, mine, seira, "Первый раз, можно с нами?")
    for signup_id in (s1, s2, s3):
        signups.confirm_signup(conn, gm, signup_id)
    signups.reject_signup(conn, gm, s4)
    signups.create_signup(conn, gleb, fog, pip)

    notes.save_game_note(
        conn,
        gm,
        mine,
        "Сцена 1. Обвал на втором ярусе\nПроход завален. Разобрать — 1 час "
        "и проверка Силы (Атлетика) СЛ 13.\n\nСцена 2. Эхо\nГолос в шахте "
        "повторяет фразы героев с задержкой.\n\nПоворот\nКарта шахты у Торбека "
        "нарисована рукой его пропавшего брата.",
    )
    notes.save_world_note(
        conn,
        gm,
        "NPC",
        "Мэтр Олдрик",
        "Трактирщик «Кривого котла». Секрет: голос в шахте Эхо — его.",
    )
    notes.save_world_note(
        conn, gm, "NPC", "Капитан Ренн", "Городская стража Серого Брода."
    )
    notes.save_world_note(
        conn, gm, "LOCATION", "Серый Брод", "Портовый город у подножия гор."
    )
    notes.save_world_note(
        conn, gm, "LORE", "Первый обвал", "Сорок лет назад шахту Эхо завалило."
    )
    conn.close()
    print(f"Демо-БД создана: {DB_PATH}")
    print("Мастер: master / 1234; Игроки: gleb, artem, elena, polina / 1234")


if __name__ == "__main__":
    main()
