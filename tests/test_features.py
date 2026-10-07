"""Тесты функций: лист ожидания, итоги и уровни, статистика, напоминание, кубики."""

import random
import unittest
from datetime import datetime, timedelta

from gm_hub.config import DATETIME_FORMAT
from gm_hub.logic import auth, characters, dice, games, notes, signups
from gm_hub.logic.errors import AccessError, ValidationError
from tests import future, make_db


def make_past_game(conn, gm_id) -> int:
    """Добавляет прошедшую сессию на 2 места (через форму её не создать)."""
    when = (datetime.now() - timedelta(days=3)).strftime(DATETIME_FORMAT)
    with conn:
        cur = conn.execute(
            "INSERT INTO Games (gm_id, title, scheduled_at, max_players, status) "
            "VALUES (?, 'Прошлая игра', ?, 2, 'CLOSED')",
            (gm_id, when),
        )
    return cur.lastrowid


class FeaturesTest(unittest.TestCase):
    """Мастер, два Игрока с персонажами."""

    def setUp(self):
        """Создаёт пользователей, персонажей и сессию на 1 место."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        for name, login, role in (
            ("Мастер", "gm", "GM"),
            ("Другой Мастер", "gm2", "GM"),
            ("Игрок 1", "p1", "PLAYER"),
            ("Игрок 2", "p2", "PLAYER"),
        ):
            auth.register(self.conn, name, login, "1234", "1234", role)
        self.gm, self.gm2, self.p1, self.p2 = (
            auth.login_user(self.conn, login, "1234")
            for login in ("gm", "gm2", "p1", "p2")
        )
        self.c1 = characters.save_character(self.conn, self.p1, "Пип", "", "", 4, "")
        self.c2 = characters.save_character(self.conn, self.p2, "Грум", "", "", 20, "")
        self.game = games.save_game(self.conn, self.gm, "Игра", "", *future(), 1)

    def confirm(self, game_id, character_id, player):
        """Подаёт и сразу подтверждает заявку."""
        signup = signups.create_signup(self.conn, player, game_id, character_id)
        signups.confirm_signup(self.conn, self.gm, signup)
        return signup

    def test_queue_when_full(self):
        """Мест нет — заявка на рассмотрении получает номер в очереди."""
        first = signups.create_signup(self.conn, self.p1, self.game, self.c1)
        self.assertEqual(signups.queue_positions(self.conn, self.game), {})
        signups.confirm_signup(self.conn, self.gm, first)
        waiting = signups.create_signup(self.conn, self.p2, self.game, self.c2)
        self.assertEqual(signups.queue_positions(self.conn, self.game), {waiting: 1})

    def test_summary_only_for_past_game(self):
        """Итоги пишутся только к прошедшей сессии и видны участнику."""
        with self.assertRaises(ValidationError):
            games.save_summary(self.conn, self.gm, self.game, "Итоги")
        past = make_past_game(self.conn, self.gm["id"])
        with self.conn:
            self.conn.execute(
                "INSERT INTO Game_Signups (game_id, character_id, status, created_at) "
                "VALUES (?, ?, 'CONFIRMED', '2026-01-01 10:00')",
                (past, self.c1),
            )
        games.save_summary(self.conn, self.gm, past, "Нашли карту шахты")
        mine = signups.list_for_player(self.conn, self.p1)
        self.assertEqual(mine[0]["game_summary"], "Нашли карту шахты")
        with self.assertRaises(AccessError):
            games.save_summary(self.conn, self.gm2, past, "Чужие итоги")

    def test_level_up_once(self):
        """Уровень участников растёт на 1 один раз, но не выше 20."""
        past = make_past_game(self.conn, self.gm["id"])
        with self.conn:
            for char in (self.c1, self.c2):
                self.conn.execute(
                    "INSERT INTO Game_Signups (game_id, character_id, status, "
                    "created_at) VALUES (?, ?, 'CONFIRMED', '2026-01-01 10:00')",
                    (past, char),
                )
        self.assertEqual(characters.level_up_after_game(self.conn, self.gm, past), 1)
        self.assertEqual(characters.get_character(self.conn, self.c1)["level"], 5)
        self.assertEqual(characters.get_character(self.conn, self.c2)["level"], 20)
        with self.assertRaises(ValidationError):
            characters.level_up_after_game(self.conn, self.gm, past)

    def test_level_up_not_for_planned(self):
        """Предстоящая сессия ещё не прошла — уровни не повышаются."""
        with self.assertRaises(ValidationError):
            characters.level_up_after_game(self.conn, self.gm, self.game)

    def test_master_stats(self):
        """Статистика: число сессий, заполняемость и активные игроки."""
        past = make_past_game(self.conn, self.gm["id"])
        with self.conn:
            self.conn.execute(
                "INSERT INTO Game_Signups (game_id, character_id, status, created_at) "
                "VALUES (?, ?, 'CONFIRMED', '2026-01-01 10:00')",
                (past, self.c1),
            )
        self.confirm(self.game, self.c1, self.p1)
        stats = games.master_stats(self.conn, self.gm)
        self.assertEqual((stats["planned"], stats["closed"]), (1, 1))
        self.assertEqual(stats["fill"], 50)  # 1 участник из 2 мест
        self.assertEqual(stats["players"], [("Игрок 1", 2)])

    def test_next_game_reminder(self):
        """Напоминание — о подтверждённой игре в ближайшие 3 дня."""
        self.confirm(self.game, self.c1, self.p1)  # игра через 7 дней
        self.assertIsNone(signups.next_game(self.conn, self.p1))
        soon = games.save_game(self.conn, self.gm, "Скоро", "", *future(2), 4)
        self.confirm(soon, self.c1, self.p1)
        self.assertEqual(signups.next_game(self.conn, self.p1)["game_title"], "Скоро")

    def test_search_game_notes(self):
        """Поиск находит сессию по тексту заметки без учёта регистра."""
        notes.save_game_note(self.conn, self.gm, self.game, "Голос в ШАХТЕ")
        self.assertEqual(
            notes.search_game_notes(self.conn, self.gm, "шахте"), {self.game}
        )
        self.assertEqual(notes.search_game_notes(self.conn, self.gm, "дракон"), set())

    def test_dice(self):
        """Кубики дают значения от 1 до числа граней."""
        values = dice.roll(20, 10, random.Random(1))
        self.assertEqual(len(values), 10)
        self.assertTrue(all(1 <= v <= 20 for v in values))
        with self.assertRaises(ValidationError):
            dice.roll(7)


if __name__ == "__main__":
    unittest.main()
