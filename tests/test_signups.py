"""Тесты подсистемы «Запись» (сценарии 5–10 и 14 п. 6.1 ТЗ)."""

import unittest

from gm_hub.logic import auth, characters, games, signups
from gm_hub.logic.errors import ValidationError
from tests import future, make_db


class SignupsTest(unittest.TestCase):
    """Подача, подтверждение и отклонение заявок."""

    def setUp(self):
        """Создаёт Мастера, двух Игроков с персонажами и сессию на 1 место."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        auth.register(self.conn, "Мастер", "gm", "1234", "1234", "GM")
        auth.register(self.conn, "Игрок 1", "p1", "1234", "1234", "PLAYER")
        auth.register(self.conn, "Игрок 2", "p2", "1234", "1234", "PLAYER")
        self.gm = auth.login_user(self.conn, "gm", "1234")
        self.p1 = auth.login_user(self.conn, "p1", "1234")
        self.p2 = auth.login_user(self.conn, "p2", "1234")
        self.char1 = characters.save_character(self.conn, self.p1, "Пип", "", "", 4, "")
        self.char2 = characters.save_character(
            self.conn, self.p2, "Грум", "", "", 3, ""
        )
        self.game = games.save_game(self.conn, self.gm, "Игра", "", *future(), 1)

    def status(self, signup_id):
        """Возвращает текущий статус заявки."""
        return self.conn.execute(
            "SELECT status FROM Game_Signups WHERE id = ?", (signup_id,)
        ).fetchone()[0]

    def test_05_signup_without_character(self):
        """Сценарий 5: без персонажа заявка не создаётся."""
        with self.assertRaises(ValidationError):
            signups.create_signup(self.conn, self.p1, self.game, None)
        self.assertEqual(signups.list_for_player(self.conn, self.p1), [])

    def test_06_signup_is_pending(self):
        """Сценарий 6: заявка создаётся со статусом «На рассмотрении»."""
        signup_id = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        self.assertEqual(self.status(signup_id), "PENDING")

    def test_07_double_signup(self):
        """Сценарий 7: повторная заявка тем же персонажем запрещена."""
        signups.create_signup(self.conn, self.p1, self.game, self.char1)
        with self.assertRaises(ValidationError):
            signups.create_signup(self.conn, self.p1, self.game, self.char1)
        self.assertEqual(len(signups.list_for_game(self.conn, self.game)), 1)

    def test_one_player_one_character(self):
        """Второй персонаж того же Игрока не записывается на ту же сессию."""
        signups.create_signup(self.conn, self.p1, self.game, self.char1)
        other = characters.save_character(self.conn, self.p1, "Корвин", "", "", 2, "")
        with self.assertRaises(ValidationError):
            signups.create_signup(self.conn, self.p1, self.game, other)
        self.assertEqual(len(signups.list_for_game(self.conn, self.game)), 1)

    def test_after_reject_other_character_allowed(self):
        """После отказа Игрок может записаться другим персонажем."""
        first = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        signups.reject_signup(self.conn, self.gm, first)
        other = characters.save_character(self.conn, self.p1, "Корвин", "", "", 2, "")
        second = signups.create_signup(self.conn, self.p1, self.game, other)
        self.assertEqual(self.status(second), "PENDING")

    def test_confirm_second_character_of_player(self):
        """Мастер не подтвердит второго персонажа Игрока на ту же сессию."""
        self.conn.execute("UPDATE Games SET max_players = 5")
        first = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        other = characters.save_character(self.conn, self.p1, "Корвин", "", "", 2, "")
        # заявка, поданная до появления правила (в старой БД), — сразу в таблицу
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO Game_Signups (game_id, character_id, status, created_at) "
                "VALUES (?, ?, 'PENDING', '2026-01-01 10:00')",
                (self.game, other),
            )
        signups.confirm_signup(self.conn, self.gm, first)
        with self.assertRaises(ValidationError):
            signups.confirm_signup(self.conn, self.gm, cur.lastrowid)
        self.assertEqual(self.status(cur.lastrowid), "PENDING")

    def test_08_confirm_over_limit(self):
        """Сценарий 8: подтвердить сверх лимита мест нельзя."""
        first = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        second = signups.create_signup(self.conn, self.p2, self.game, self.char2)
        signups.confirm_signup(self.conn, self.gm, first)
        with self.assertRaises(ValidationError):
            signups.confirm_signup(self.conn, self.gm, second)
        self.assertEqual(self.status(second), "PENDING")

    def test_09_confirm_within_limit(self):
        """Сценарий 9: подтверждение в пределах лимита, Игрок видит статус."""
        signup_id = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        signups.confirm_signup(self.conn, self.gm, signup_id)
        mine = signups.list_for_player(self.conn, self.p1)
        self.assertEqual(mine[0]["status"], "CONFIRMED")
        self.assertIsNotNone(mine[0]["decided_at"])

    def test_10_reject(self):
        """Сценарий 10: отклонённая заявка получает статус «Отклонена»."""
        signup_id = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        signups.reject_signup(self.conn, self.gm, signup_id)
        self.assertEqual(self.status(signup_id), "REJECTED")

    def test_14_player_sees_only_own_signups(self):
        """Сценарий 14: в «Мои записи» только заявки текущего Игрока."""
        signups.create_signup(self.conn, self.p1, self.game, self.char1)
        signups.create_signup(self.conn, self.p2, self.game, self.char2)
        mine = signups.list_for_player(self.conn, self.p1)
        self.assertEqual([row["character_name"] for row in mine], ["Пип"])

    def test_withdraw(self):
        """Игрок может отозвать заявку на рассмотрении."""
        signup_id = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        signups.withdraw_signup(self.conn, self.p1, signup_id)
        self.assertEqual(signups.list_for_player(self.conn, self.p1), [])

    def test_reject_with_reason(self):
        """Причина отказа сохраняется, Игрок её видит."""
        signup_id = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        signups.reject_signup(self.conn, self.gm, signup_id, "Нет мест для новичков")
        mine = signups.list_for_player(self.conn, self.p1)
        self.assertEqual(mine[0]["reason"], "Нет мест для новичков")

    def test_cancel_game_rejects_pending(self):
        """При отмене сессии заявки на рассмотрении отклоняются."""
        signup_id = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        games.cancel_game(self.conn, self.gm, self.game)
        self.assertEqual(self.status(signup_id), "REJECTED")
        mine = signups.list_for_player(self.conn, self.p1)
        self.assertEqual(mine[0]["reason"], "Сессия отменена")

    def test_withdraw_confirmed_frees_seat(self):
        """Подтверждённую заявку можно отозвать — место освобождается."""
        first = signups.create_signup(self.conn, self.p1, self.game, self.char1)
        second = signups.create_signup(self.conn, self.p2, self.game, self.char2)
        signups.confirm_signup(self.conn, self.gm, first)
        signups.withdraw_signup(self.conn, self.p1, first)
        signups.confirm_signup(self.conn, self.gm, second)
        self.assertEqual(self.status(second), "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
