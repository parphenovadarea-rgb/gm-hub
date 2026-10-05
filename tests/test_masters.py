"""Тесты разделения Мастеров: у каждого свои сессии, заявки и заметки."""

import unittest

from gm_hub.logic import auth, characters, games, notes, signups
from gm_hub.logic.errors import AccessError
from tests import future, make_db


class MastersTest(unittest.TestCase):
    """Два Мастера и Игрок, который выбирает Мастера."""

    def setUp(self):
        """Создаёт двух Мастеров с сессиями и Игрока с персонажем."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        auth.register(self.conn, "Ильин Максим", "ilin", "1234", "1234", "GM")
        auth.register(self.conn, "Агыг", "агыг", "1234", "1234", "GM")
        auth.register(self.conn, "Игрок", "pl", "1234", "1234", "PLAYER")
        self.gm1 = auth.login_user(self.conn, "ilin", "1234")
        self.gm2 = auth.login_user(self.conn, "агыг", "1234")
        self.player = auth.login_user(self.conn, "pl", "1234")
        self.game1 = games.save_game(self.conn, self.gm1, "Игра 1", "", *future(), 4)
        self.game2 = games.save_game(self.conn, self.gm2, "Игра 2", "", *future(), 4)

    def test_each_master_sees_own_games(self):
        """В расписании Мастера только его сессии."""
        mine = games.list_games(self.conn, gm_id=self.gm1["id"])
        self.assertEqual([g["title"] for g in mine], ["Игра 1"])

    def test_cannot_change_other_master_game(self):
        """Чужую сессию нельзя изменить, отменить или удалить."""
        with self.assertRaises(AccessError):
            games.save_game(self.conn, self.gm1, "Чужая", "", *future(), 4, self.game2)
        with self.assertRaises(AccessError):
            games.cancel_game(self.conn, self.gm1, self.game2)
        self.assertEqual(games.get_game(self.conn, self.game2)["title"], "Игра 2")

    def test_cannot_confirm_other_master_signup(self):
        """Заявку на чужую сессию нельзя подтвердить или отклонить."""
        char = characters.save_character(self.conn, self.player, "Пип", "", "", 4, "")
        signup = signups.create_signup(self.conn, self.player, self.game2, char)
        with self.assertRaises(AccessError):
            signups.confirm_signup(self.conn, self.gm1, signup)
        with self.assertRaises(AccessError):
            signups.reject_signup(self.conn, self.gm1, signup)

    def test_notes_are_private(self):
        """Заметки и база мира одного Мастера не видны другому."""
        notes.save_game_note(self.conn, self.gm2, self.game2, "секрет")
        with self.assertRaises(AccessError):
            notes.get_game_note(self.conn, self.gm1, self.game2)
        note_id = notes.save_world_note(self.conn, self.gm2, "NPC", "Олдрик", "")
        self.assertEqual(notes.list_world_notes(self.conn, self.gm1), [])
        with self.assertRaises(AccessError):
            notes.delete_world_note(self.conn, self.gm1, note_id)

    def test_player_finds_master_by_name(self):
        """Игрок находит Мастера по части имени без учёта регистра."""
        found = auth.list_masters(self.conn, "ИЛЬ")
        self.assertEqual([m["full_name"] for m in found], ["Ильин Максим"])
        self.assertEqual(len(auth.list_masters(self.conn)), 2)


if __name__ == "__main__":
    unittest.main()
