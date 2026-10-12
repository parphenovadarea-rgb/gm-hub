"""Тесты граничных условий, обработки ошибок и безопасности (SQL-инъекции, права)."""

import random
import sqlite3
import unittest
from datetime import datetime, timedelta

from gm_hub.config import DATETIME_FORMAT, to_short
from gm_hub.db.database import add_column, connect, init_db
from gm_hub.logic import auth, characters, dice, games, notes, signups
from gm_hub.logic.errors import AccessError, ValidationError
from tests import future, make_db

INJECTIONS = [
    "' OR '1'='1",
    "admin'--",
    "x'; DROP TABLE Users; --",
    '" OR ""="',
    "1; DELETE FROM Games",
]


def add_past_game(conn, gm_id) -> int:
    """Добавляет прошедшую (закрытую) сессию — через форму её не создать."""
    when = (datetime.now() - timedelta(days=2)).strftime(DATETIME_FORMAT)
    with conn:
        cur = conn.execute(
            "INSERT INTO Games (gm_id, title, scheduled_at, max_players, status) "
            "VALUES (?, 'Прошлая', ?, 3, 'CLOSED')",
            (gm_id, when),
        )
    return cur.lastrowid


class EdgeCase(unittest.TestCase):
    """Основа: БД в памяти, два Мастера, Игрок, сессия и персонаж."""

    def setUp(self):
        """Создаёт данные для теста."""
        self.conn = make_db()
        for name, login, role in (
            ("Мастер Один", "gm1", "GM"),
            ("Мастер Два", "gm2", "GM"),
            ("Игрок Один", "pl1", "PLAYER"),
            ("Игрок Два", "pl2", "PLAYER"),
        ):
            auth.register(self.conn, name, login, "1234", "1234", role)
        self.gm1 = auth.login_user(self.conn, "gm1", "1234")
        self.gm2 = auth.login_user(self.conn, "gm2", "1234")
        self.pl1 = auth.login_user(self.conn, "pl1", "1234")
        self.pl2 = auth.login_user(self.conn, "pl2", "1234")
        date, time = future(4)
        self.game = games.save_game(self.conn, self.gm1, "Игра", "", date, time, 2)
        self.hero1 = characters.save_character(
            self.conn, self.pl1, "Пип", "Эльф", "Плут", 3, ""
        )
        self.hero2 = characters.save_character(
            self.conn, self.pl2, "Грум", "Орк", "Воин", 3, ""
        )
        self.addCleanup(self.conn.close)


class AuthEdgeTest(EdgeCase):
    """Регистрация, вход, профиль: граничные значения."""

    def test_short_password(self):
        """Пароль из 3 символов не принимается, из 4 — принимается."""
        with self.assertRaises(ValidationError):
            auth.register(self.conn, "Тест", "t1", "123", "123", "PLAYER")
        auth.register(self.conn, "Тест", "t2", "1234", "1234", "PLAYER")

    def test_password_mismatch(self):
        """Разные пароли в двух полях — ошибка в поле «Повтор»."""
        with self.assertRaises(ValidationError) as caught:
            auth.register(self.conn, "Тест", "t3", "1234", "4321", "PLAYER")
        self.assertEqual(caught.exception.field, "Повтор")

    def test_wrong_role(self):
        """Неизвестная роль не принимается."""
        with self.assertRaises(ValidationError):
            auth.register(self.conn, "Тест", "t4", "1234", "1234", "ADMIN")

    def test_unknown_login(self):
        """Вход под несуществующим логином — ошибка без уточнений."""
        with self.assertRaises(ValidationError) as caught:
            auth.login_user(self.conn, "нет_такого", "1234")
        self.assertIn("Неверный логин или пароль", caught.exception.message)

    def test_profile_wrong_password(self):
        """Профиль не меняется, если текущий пароль неверный."""
        with self.assertRaises(ValidationError):
            auth.update_profile(self.conn, self.pl1, "Другое имя", "0000")
        name = self.conn.execute(
            "SELECT full_name FROM Users WHERE id = ?", (self.pl1["id"],)
        ).fetchone()[0]
        self.assertEqual(name, "Игрок Один")

    def test_profile_change_name_and_password(self):
        """ФИО и пароль меняются, старый пароль перестаёт работать."""
        auth.update_profile(self.conn, self.pl1, "Новое Имя", "1234", "5678", "5678")
        self.assertEqual(
            auth.login_user(self.conn, "pl1", "5678")["full_name"], "Новое Имя"
        )
        with self.assertRaises(ValidationError):
            auth.login_user(self.conn, "pl1", "1234")

    def test_delete_account_blocked_by_data(self):
        """Аккаунт с персонажами или сессиями удалить нельзя."""
        with self.assertRaises(ValidationError):
            auth.delete_account(self.conn, self.pl1, "1234")
        with self.assertRaises(ValidationError):
            auth.delete_account(self.conn, self.gm1, "1234")

    def test_delete_empty_account(self):
        """Аккаунт без данных удаляется, логин освобождается."""
        auth.register(self.conn, "Пустой", "empty", "1234", "1234", "PLAYER")
        user = auth.login_user(self.conn, "empty", "1234")
        auth.delete_account(self.conn, user, "1234")
        with self.assertRaises(ValidationError):
            auth.login_user(self.conn, "empty", "1234")


class CharacterEdgeTest(EdgeCase):
    """Персонажи: уровень и права."""

    def test_level_bounds(self):
        """Уровни 1 и 20 допустимы, 0 и 21 — нет."""
        self.assertEqual(characters.check_level("1"), 1)
        self.assertEqual(characters.check_level(" 20 "), 20)
        for bad in ("0", "21", "-5", "abc", "", "1.5"):
            with self.assertRaises(ValidationError, msg=bad):
                characters.check_level(bad)

    def test_empty_name(self):
        """Имя персонажа обязательно."""
        with self.assertRaises(ValidationError):
            characters.save_character(self.conn, self.pl1, "  ", "", "", 1, "")

    def test_delete_foreign_character(self):
        """Чужого персонажа удалить нельзя."""
        with self.assertRaises(AccessError):
            characters.delete_character(self.conn, self.pl2, self.hero1)

    def test_level_up_requires_past_game(self):
        """Повысить уровни можно только после прошедшей сессии."""
        with self.assertRaises(ValidationError):
            characters.level_up_after_game(self.conn, self.gm1, self.game)


class GameEdgeTest(EdgeCase):
    """Сессии: даты, лимиты, права."""

    def test_bad_dates(self):
        """Несуществующая дата, нечисловая дата и пустое поле — ошибки."""
        date, time = future(3)
        for bad_date, bad_time in (
            ("31.02.2030", "18:00"),
            ("abc", "18:00"),
            (date, "25:99"),
        ):
            with self.assertRaises(ValidationError, msg=(bad_date, bad_time)):
                games.parse_datetime(bad_date, bad_time)
        with self.assertRaises(ValidationError):
            games.parse_datetime("", time)

    def test_past_date(self):
        """Дата в прошлом не принимается."""
        with self.assertRaises(ValidationError):
            games.parse_datetime("01.01.2020", "10:00")

    def test_max_players_bounds(self):
        """Лимит мест: 1 допустимо, 0, отрицательное и текст — нет."""
        self.assertEqual(games.check_max_players("1"), 1)
        for bad in ("0", "-3", "abc", "", "2.5"):
            with self.assertRaises(ValidationError, msg=bad):
                games.check_max_players(bad)

    def test_limit_cannot_be_below_confirmed(self):
        """Лимит нельзя сделать меньше числа подтверждённых заявок."""
        for hero, user in ((self.hero1, self.pl1), (self.hero2, self.pl2)):
            signup = signups.create_signup(self.conn, user, self.game, hero)
            signups.confirm_signup(self.conn, self.gm1, signup)
        date, time = future(4)
        with self.assertRaises(ValidationError):
            games.save_game(self.conn, self.gm1, "Игра", "", date, time, 1, self.game)
        games.save_game(self.conn, self.gm1, "Игра", "", date, time, 2, self.game)

    def test_foreign_game_is_protected(self):
        """Другой Мастер не может ни изменить, ни отменить, ни удалить сессию."""
        date, time = future(4)
        with self.assertRaises(AccessError):
            games.save_game(self.conn, self.gm2, "Моя", "", date, time, 2, self.game)
        with self.assertRaises(AccessError):
            games.cancel_game(self.conn, self.gm2, self.game)
        with self.assertRaises(AccessError):
            games.delete_game(self.conn, self.gm2, self.game)

    def test_player_cannot_create_game(self):
        """Игрок не может создавать сессии."""
        date, time = future(4)
        with self.assertRaises(AccessError):
            games.save_game(self.conn, self.pl1, "Игра", "", date, time, 2)

    def test_delete_planned_game_is_forbidden(self):
        """Предстоящую сессию удалить нельзя — сначала отменить."""
        with self.assertRaises(ValidationError):
            games.delete_game(self.conn, self.gm1, self.game)

    def test_summary_only_for_past_game(self):
        """Итоги можно писать только к прошедшей сессии."""
        with self.assertRaises(ValidationError):
            games.save_summary(self.conn, self.gm1, self.game, "итоги")
        past = add_past_game(self.conn, self.gm1["id"])
        games.save_summary(self.conn, self.gm1, past, "Нашли карту")
        self.assertEqual(games.get_game(self.conn, past)["summary"], "Нашли карту")

    def test_in_period_boundaries(self):
        """Период «7 дней»: граница включается, дальше — нет."""
        now = datetime(2030, 1, 1, 12, 0)
        edge = (now + timedelta(days=7)).strftime(DATETIME_FORMAT)
        later = (now + timedelta(days=7, minutes=1)).strftime(DATETIME_FORMAT)
        self.assertTrue(games.in_period(edge, 7, now))
        self.assertFalse(games.in_period(later, 7, now))
        self.assertTrue(games.in_period(later, None, now))


class SignupEdgeTest(EdgeCase):
    """Заявки: недопустимые действия."""

    def test_signup_without_game(self):
        """Без выбранной сессии заявка не создаётся."""
        with self.assertRaises(ValidationError):
            signups.create_signup(self.conn, self.pl1, None, self.hero1)

    def test_signup_with_foreign_character(self):
        """Заявку можно подать только своим персонажем."""
        with self.assertRaises(AccessError):
            signups.create_signup(self.conn, self.pl1, self.game, self.hero2)

    def test_signup_on_cancelled_game(self):
        """На отменённую сессию запись закрыта."""
        games.cancel_game(self.conn, self.gm1, self.game)
        with self.assertRaises(ValidationError):
            signups.create_signup(self.conn, self.pl1, self.game, self.hero1)

    def test_withdraw_foreign_or_rejected(self):
        """Чужую или отклонённую заявку отозвать нельзя."""
        signup = signups.create_signup(self.conn, self.pl1, self.game, self.hero1)
        with self.assertRaises(ValidationError):
            signups.withdraw_signup(self.conn, self.pl2, signup)
        signups.reject_signup(self.conn, self.gm1, signup, "мест нет")
        with self.assertRaises(ValidationError):
            signups.withdraw_signup(self.conn, self.pl1, signup)

    def test_decide_twice(self):
        """Подтвердить повторно или отклонить уже отклонённую нельзя."""
        signup = signups.create_signup(self.conn, self.pl1, self.game, self.hero1)
        signups.confirm_signup(self.conn, self.gm1, signup)
        with self.assertRaises(ValidationError):
            signups.confirm_signup(self.conn, self.gm1, signup)
        other = signups.create_signup(self.conn, self.pl2, self.game, self.hero2)
        signups.reject_signup(self.conn, self.gm1, other)
        with self.assertRaises(ValidationError):
            signups.reject_signup(self.conn, self.gm1, other)

    def test_foreign_master_cannot_decide(self):
        """Мастер не может решать заявки на чужую сессию, Игрок — вообще."""
        signup = signups.create_signup(self.conn, self.pl1, self.game, self.hero1)
        with self.assertRaises(AccessError):
            signups.confirm_signup(self.conn, self.gm2, signup)
        with self.assertRaises(AccessError):
            signups.confirm_signup(self.conn, self.pl1, signup)


class NotesEdgeTest(EdgeCase):
    """Заметки и база мира."""

    def test_note_requires_game(self):
        """Заметку без выбранной сессии сохранить или удалить нельзя."""
        with self.assertRaises(ValidationError):
            notes.save_game_note(self.conn, self.gm1, None, "текст")
        with self.assertRaises(ValidationError):
            notes.delete_game_note(self.conn, self.gm1, None)

    def test_note_save_update_delete(self):
        """Заметка создаётся, обновляется и удаляется."""
        notes.save_game_note(self.conn, self.gm1, self.game, "первая")
        notes.save_game_note(self.conn, self.gm1, self.game, "вторая")
        self.assertEqual(
            notes.get_game_note(self.conn, self.gm1, self.game)["content"], "вторая"
        )
        notes.delete_game_note(self.conn, self.gm1, self.game)
        self.assertIsNone(notes.get_game_note(self.conn, self.gm1, self.game))

    def test_foreign_master_has_no_access_to_notes(self):
        """Заметки чужой сессии недоступны другому Мастеру."""
        with self.assertRaises(AccessError):
            notes.get_game_note(self.conn, self.gm2, self.game)

    def test_search_is_case_insensitive(self):
        """Поиск ищет и в названии, и в тексте, без учёта регистра."""
        notes.save_game_note(self.conn, self.gm1, self.game, "Драконы Севера")
        self.assertEqual(
            notes.search_game_notes(self.conn, self.gm1, "ДРАКОН"), {self.game}
        )
        self.assertEqual(
            notes.search_game_notes(self.conn, self.gm1, "игра"), {self.game}
        )
        self.assertEqual(
            notes.search_game_notes(self.conn, self.gm1, "нет такого"), set()
        )

    def test_world_notes_crud_and_filter(self):
        """Запись базы мира: создать, изменить, найти, удалить."""
        note = notes.save_world_note(
            self.conn, self.gm1, "NPC", "Вейла", "Глава гильдии"
        )
        notes.save_world_note(self.conn, self.gm1, "LORE", "Обвал", "", None)
        notes.save_world_note(self.conn, self.gm1, "NPC", "Вейла Серебряная", "", note)
        found = notes.list_world_notes(self.conn, self.gm1, "NPC", "серебр")
        self.assertEqual([row["title"] for row in found], ["Вейла Серебряная"])
        self.assertEqual(len(notes.list_world_notes(self.conn, self.gm1)), 2)
        notes.delete_world_note(self.conn, self.gm1, note)
        self.assertEqual(len(notes.list_world_notes(self.conn, self.gm1)), 1)

    def test_world_note_validation(self):
        """Без категории и без заголовка запись не сохраняется."""
        with self.assertRaises(ValidationError):
            notes.save_world_note(self.conn, self.gm1, "", "Заголовок", "")
        with self.assertRaises(ValidationError):
            notes.save_world_note(self.conn, self.gm1, "NPC", "  ", "")

    def test_world_is_private(self):
        """Чужую запись базы мира нельзя ни прочитать, ни изменить."""
        note = notes.save_world_note(self.conn, self.gm1, "LORE", "Секрет", "")
        with self.assertRaises(AccessError):
            notes.get_world_note(self.conn, self.gm2, note)
        with self.assertRaises(AccessError):
            notes.save_world_note(self.conn, self.gm2, "LORE", "Взлом", "", note)
        self.assertEqual(notes.list_world_notes(self.conn, self.gm2), [])


class MiscEdgeTest(unittest.TestCase):
    """Мелкие функции и база данных."""

    def test_dice_bounds(self):
        """Кубики: 1–10 штук, только стандартные грани."""
        rng = random.Random(1)
        self.assertEqual(len(dice.roll(20, 10, rng)), 10)
        for sides, count in ((7, 1), (20, 0), (20, 11)):
            with self.assertRaises(ValidationError, msg=(sides, count)):
                dice.roll(sides, count)
        self.assertTrue(all(1 <= v <= 6 for v in dice.roll(6, 10, rng)))

    def test_short_date_without_value(self):
        """Пустая дата показывается прочерком."""
        self.assertEqual(to_short(None), "—")

    def test_init_db_is_repeatable(self):
        """Повторное создание таблиц ничего не ломает."""
        conn = make_db()
        init_db(conn)
        init_db(conn)

    def test_old_database_gets_new_column(self):
        """В базе старой версии новый столбец добавляется сам."""
        conn = connect(":memory:")
        conn.execute("CREATE TABLE Games (id INTEGER PRIMARY KEY, title TEXT)")
        add_column(conn, "Games", "summary", "TEXT")
        names = [row["name"] for row in conn.execute("PRAGMA table_info(Games)")]
        self.assertIn("summary", names)
        add_column(conn, "Games", "summary", "TEXT")  # повтор безопасен


class SecurityTest(EdgeCase):
    """Базовая проверка безопасности: SQL-инъекции, пароли, права, ключи."""

    def tables_intact(self):
        """Таблицы на месте, данные не пропали."""
        names = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue({"Users", "Games", "Characters", "Game_Signups"} <= names)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 4
        )
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM Games").fetchone()[0], 1
        )

    def test_login_injection(self):
        """Строки-инъекции вместо логина и пароля не дают войти."""
        for text in INJECTIONS:
            with self.assertRaises(ValidationError, msg=text):
                auth.login_user(self.conn, text, text)
            with self.assertRaises(ValidationError, msg=text):
                auth.login_user(self.conn, "gm1", text)
        self.tables_intact()

    def test_registration_stores_injection_as_text(self):
        """Логин с кавычками и SQL сохраняется как обычный текст."""
        for number, text in enumerate(INJECTIONS):
            login = f"{text}{number}"
            auth.register(
                self.conn, f"Хитрец {number}", login, "1234", "1234", "PLAYER"
            )
            self.assertEqual(auth.login_user(self.conn, login, "1234")["login"], login)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0],
            4 + len(INJECTIONS),
        )
        self.assertIn(
            "Users",
            {row[0] for row in self.conn.execute("SELECT name FROM sqlite_master")},
        )

    def test_text_fields_and_search_with_injection(self):
        """Заметки, база мира, поиск и комментарий принимают инъекции как текст."""
        for text in INJECTIONS:
            notes.save_game_note(self.conn, self.gm1, self.game, text)
            note = notes.save_world_note(self.conn, self.gm1, "LORE", text, text)
            self.assertEqual(
                notes.get_world_note(self.conn, self.gm1, note)["title"], text
            )
            notes.search_game_notes(self.conn, self.gm1, text)
            notes.list_world_notes(self.conn, self.gm1, None, text)
            auth.list_masters(self.conn, text)
        self.tables_intact()

    def test_signup_comment_with_injection(self):
        """Комментарий к заявке с SQL сохраняется буквально."""
        text = "'); DELETE FROM Game_Signups; --"
        signup = signups.create_signup(self.conn, self.pl1, self.game, self.hero1, text)
        rows = signups.list_for_game(self.conn, self.game)
        self.assertEqual([r["comment"] for r in rows], [text])
        self.assertEqual(rows[0]["id"], signup)

    def test_passwords_are_hashed_and_salted(self):
        """Пароль не хранится открыто; одинаковые пароли дают разные хэши."""
        hashes = [
            row[0]
            for row in self.conn.execute("SELECT password_hash FROM Users ORDER BY id")
        ]
        self.assertEqual(len(set(hashes)), len(hashes))  # у всех пароль «1234»
        for stored in hashes:
            self.assertNotIn("1234", stored)
            self.assertIn("$", stored)
            self.assertTrue(auth.check_password("1234", stored))
            self.assertFalse(auth.check_password("1235", stored))

    def test_roles_are_enforced_in_logic(self):
        """Игрок не может вызвать функции Мастера, даже минуя окна."""
        with self.assertRaises(AccessError):
            notes.list_world_notes(self.conn, self.pl1)
        with self.assertRaises(AccessError):
            notes.search_game_notes(self.conn, self.pl1, "")
        with self.assertRaises(AccessError):
            games.master_stats(self.conn, self.pl1)
        with self.assertRaises(AccessError):
            signups.export_participants(self.conn, self.pl1, self.game, "x.csv")

    def test_foreign_keys_are_enabled(self):
        """База не принимает заявку на несуществующую сессию."""
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute(
                    "INSERT INTO Game_Signups (game_id, character_id, created_at) "
                    "VALUES (999, ?, '2030-01-01 10:00')",
                    (self.hero1,),
                )

    def test_check_constraints(self):
        """Ограничения CHECK в таблицах: роль, уровень, лимит мест."""
        bad = [
            "INSERT INTO Users (full_name, login, password_hash, role, created_at) "
            "VALUES ('x', 'x', 'x', 'ROOT', '2030-01-01 10:00')",
            "INSERT INTO Characters (user_id, name, level) VALUES (1, 'x', 99)",
            "INSERT INTO Games (gm_id, title, scheduled_at, max_players) "
            "VALUES (1, 'x', '2030-01-01 10:00', 0)",
        ]
        for sql in bad:
            with self.assertRaises(sqlite3.IntegrityError, msg=sql):
                with self.conn:
                    self.conn.execute(sql)

    def test_failed_operation_leaves_no_partial_changes(self):
        """Ошибка в транзакции откатывает все изменения."""
        before = self.conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute(
                    "INSERT INTO Users (full_name, login, password_hash, role, "
                    "created_at) VALUES ('Новый', 'rollback', 'h', 'GM', "
                    "'2030-01-01 10:00')"
                )
                self.conn.execute(  # нарушает UNIQUE(login) и откатывает первую вставку
                    "INSERT INTO Users (full_name, login, password_hash, role, "
                    "created_at) VALUES ('Дубль', 'gm1', 'h', 'GM', '2030-01-01 10:00')"
                )
        after = self.conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
