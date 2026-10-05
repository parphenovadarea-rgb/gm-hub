"""Создаёт демонстрационную БД с данными из макетов Figma: python seed.py.

Внимание: старый файл gm_hub.db удаляется. Чтобы не трогать рабочую БД,
передайте другой файл: py seed.py demo.db

Даты сессий считаются от текущего дня так же, как в макетах они считались
от 29.09.2026: «Туман над Серым Бродом» через 2 дня, «Шахта Эхо, ч. 3» через 5
и т. д. Поэтому на защите сессии всегда предстоящие.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from gm_hub.config import DB_PATH, DATETIME_FORMAT, now_str
from gm_hub.db.database import connect, init_db
from gm_hub.logic import auth, characters, games, notes, signups

PASSWORD = "1234"  # пароль у всех демо-пользователей

# (ФИО, логин, роль)
USERS = [
    ("Агыг", "агыг", "GM"),
    ("Ильин Максим", "ilin", "GM"),
    ("Денисов Глеб", "gleb", "PLAYER"),
    ("Жукова Полина", "polina", "PLAYER"),
    ("Соколов Артём", "artem", "PLAYER"),
    ("Кравцова Елена", "elena", "PLAYER"),
    ("Белов Никита", "nikita", "PLAYER"),
    ("Орлова Вера", "vera", "PLAYER"),
]

# fmt: off
# (логин владельца, имя, раса, класс, уровень, предыстория)
CHARACTERS = [
    (
        "gleb", "Пип", "Полурослик", "Плут", 4,
        "Вырос в Сером Броде, в семье пекаря. В 14 лет попался на краже карты у "
        "гильдии картографов, с тех пор должен им услугу. Боится темноты, но "
        "скрывает это. Мечтает найти в шахте Эхо что-нибудь, чем можно откупиться "
        "от гильдии.",
    ),
    ("gleb", "Корвин", "Человек", "Волшебник", 2, "Ученик городского мага."),
    (
        "polina", "Сэйра", "Человек", "Паладин", 1,
        "Послушница храма Солнца, сбежала после пожара в обители и ищет того, "
        "кто его устроил.",
    ),
    ("artem", "Торбек", "Дварф", "Жрец", 4, "Ищет пропавшего брата Хальварда."),
    ("elena", "Эйлин", "Эльф", "Следопыт", 4, "Проводник по горным тропам."),
    ("nikita", "Грум", "Полуорк", "Варвар", 3, "Бывший охранник каравана."),
    ("vera", "Миралла", "Тифлинг", "Колдун", 4, "Договор с голосом из шахты."),
]

# (название, описание, через сколько дней, время, лимит мест)
GAMES = [
    ("Туман над Серым Бродом", "Расследование в портовом городе, 3–4 уровень",
     2, "19:00", 4),
    ("Шахта Эхо, ч. 3", "Спуск на нижние ярусы, 4 уровень", 5, "18:00", 5),
    ("Ваншот: ограбление храма Солнца",
     "Одна встреча на 4 часа, 1–3 уровень, новичкам можно", 12, "16:00", 4),
    ("Шахта Эхо, ч. 4", "Финал арки, 4–5 уровень", 19, "18:00", 5),
]

# (сессия, персонаж, комментарий, итоговый статус)
SIGNUPS = [
    ("Туман над Серым Бродом", "Торбек", "", "CONFIRMED"),
    ("Туман над Серым Бродом", "Эйлин", "", "CONFIRMED"),
    ("Туман над Серым Бродом", "Грум", "", "CONFIRMED"),
    ("Туман над Серым Бродом", "Миралла", "", "CONFIRMED"),
    ("Туман над Серым Бродом", "Пип", "", "REJECTED"),
    ("Туман над Серым Бродом", "Сэйра", "", "PENDING"),
    ("Шахта Эхо, ч. 3", "Миралла", "", "CONFIRMED"),
    ("Шахта Эхо, ч. 3", "Грум", "", "CONFIRMED"),
    ("Шахта Эхо, ч. 3", "Эйлин", "", "CONFIRMED"),
    ("Шахта Эхо, ч. 3", "Торбек", "", "CONFIRMED"),
    ("Шахта Эхо, ч. 3", "Пип", "Приду к 18:15", "CONFIRMED"),
    ("Шахта Эхо, ч. 3", "Корвин", "Если Пип не пройдёт", "REJECTED"),
    ("Шахта Эхо, ч. 3", "Сэйра", "Первый раз, можно с нами?", "PENDING"),
    ("Ваншот: ограбление храма Солнца", "Миралла", "", "CONFIRMED"),
    ("Ваншот: ограбление храма Солнца", "Сэйра", "", "PENDING"),
]

MINE_NOTE = """Сцена 1. Обвал на втором ярусе
Проход завален. Разобрать — 1 час и проверка Силы (Атлетика) СЛ 13. \
Альтернатива: вентиляционная шахта, пролезет только Пип.

Сцена 2. Эхо
Голос в шахте повторяет фразы героев с задержкой. Если Миралла заговорит \
со своим покровителем, эхо отвечает его голосом. Не раскрывать, что это Олдрик!

Поворот
Карта шахты у Торбека нарисована рукой его пропавшего брата."""

FOG_NOTE = """Завязка
В порт Серого Брода входит корабль без команды. Капитан Ренн просит помощи.

Улики
Судовой журнал обрывается на слове «Эхо»."""

# (категория, заголовок, текст)
WORLD = [
    ("NPC", "Мэтр Олдрик",
     "Трактирщик «Кривого котла».\n\nВнешность: лысый, седая борода заплетена "
     "в косу, на левой руке нет двух пальцев.\nНа виду: добродушный трактирщик, "
     "знает все слухи Серого Брода, наливает героям в долг.\nСекрет: бывший "
     "шахтёр, единственный выживший после первого обвала. Голос в шахте Эхо — "
     "его.\nСвязи: должен гильдии картографов; боится капитана Ренна."),
    ("NPC", "Вейла Серебряная Нить", "Глава гильдии картографов."),
    ("NPC", "Капитан Ренн", "Городская стража Серого Брода."),
    ("NPC", "Брат Хальвард", "Пропавший брат Торбека."),
    ("NPC", "Скрипун", "Кобольд-проводник."),
    ("LORE", "Первый обвал", "Сорок лет назад шахту Эхо завалило."),
    ("LORE", "Гильдия картографов", "Продаёт карты шахты втридорога."),
    ("LOCATION", "Серый Брод", "Портовый город у подножия гор."),
    ("LOCATION", "Шахта Эхо", "Заброшенная шахта к северу от города."),
    ("LOCATION", "Таверна «Кривой котёл»", "Главное место встреч героев."),
]
# fmt: on


def in_days(days: int) -> str:
    """Возвращает дату через days дней в формате формы «ДД.ММ.ГГГГ».

    Args:
        days: Через сколько дней (может быть отрицательным).

    Returns:
        Дата строкой.
    """
    return (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")


def main(path=DB_PATH) -> None:
    """Заполняет БД пользователями, персонажами, сессиями, заявками и заметками.

    Args:
        path: Файл БД. По умолчанию — рабочая БД программы (она стирается!).
    """
    path = Path(path)
    path.unlink(missing_ok=True)
    conn = connect(path)
    init_db(conn)

    users = {}
    for full_name, login, role in USERS:
        auth.register(conn, full_name, login, PASSWORD, PASSWORD, role)
        users[login] = auth.login_user(conn, login, PASSWORD)
    gm = users["агыг"]
    # Второй Мастер со своей сессией — показать, что у каждого Мастера своё окно.
    games.save_game(
        conn,
        users["ilin"],
        "Подземелья Чёрной Башни",
        "Классическое подземелье, 1–2 уровень",
        in_days(8),
        "17:00",
        5,
    )

    chars = {}
    for login, name, race, cls, level, story in CHARACTERS:
        chars[name] = characters.save_character(
            conn, users[login], name, race, cls, level, story
        )

    game_ids = {}
    for title, description, days, time, limit in GAMES:
        game_ids[title] = games.save_game(
            conn, gm, title, description, in_days(days), time, limit
        )

    for title, name, comment, status in SIGNUPS:
        owner = next(users[c[0]] for c in CHARACTERS if c[1] == name)
        signup_id = signups.create_signup(
            conn, owner, game_ids[title], chars[name], comment
        )
        if status == "CONFIRMED":
            signups.confirm_signup(conn, gm, signup_id)
        elif status == "REJECTED":
            signups.reject_signup(conn, gm, signup_id)

    # Все заявки созданы «сейчас»; чтобы даты подачи и решения различались,
    # как в макетах, сдвигаем их на несколько дней назад.
    ids = [row[0] for row in conn.execute("SELECT id FROM Game_Signups ORDER BY id")]
    with conn:
        for index, signup_id in enumerate(ids):
            created = datetime.now() - timedelta(
                hours=100 - index * 6, minutes=index * 7
            )
            decided = created + timedelta(hours=3, minutes=11)
            conn.execute(
                "UPDATE Game_Signups SET created_at = ?, decided_at = CASE "
                "WHEN decided_at IS NULL THEN NULL ELSE ? END WHERE id = ?",
                (
                    created.strftime(DATETIME_FORMAT),
                    decided.strftime(DATETIME_FORMAT),
                    signup_id,
                ),
            )

    # Прошедшую сессию через форму создать нельзя (дата в прошлом),
    # поэтому для демонстрации она добавляется напрямую.
    past = (datetime.now() - timedelta(days=9)).replace(hour=18, minute=0)
    with conn:
        conn.execute(
            "INSERT INTO Games (gm_id, title, description, scheduled_at, "
            "max_players, status) VALUES (?, ?, ?, ?, ?, 'CLOSED')",
            (
                gm["id"],
                "Шахта Эхо, ч. 2",
                "Первый спуск в шахту",
                past.strftime(DATETIME_FORMAT),
                5,
            ),
        )

    notes.save_game_note(conn, gm, game_ids["Шахта Эхо, ч. 3"], MINE_NOTE)
    notes.save_game_note(conn, gm, game_ids["Туман над Серым Бродом"], FOG_NOTE)
    for category, title, text in WORLD:
        notes.save_world_note(conn, gm, category, title, text)

    conn.close()
    print(f"Демо-БД создана {now_str()}: {path}")
    print(f"Мастера: агыг, ilin / {PASSWORD}")
    print(f"Игроки: gleb, polina, artem, elena, nikita, vera / {PASSWORD}")


if __name__ == "__main__":
    # py seed.py demo.db — создать демо-БД в другом файле, не трогая рабочую.
    main(sys.argv[1] if len(sys.argv) > 1 else DB_PATH)
