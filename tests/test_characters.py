"""Тесты подсистемы «Персонажи» (сценарий 13 п. 6.1 ТЗ)."""

import unittest

from gm_hub.logic import auth, characters, games, signups
from gm_hub.logic.errors import ValidationError
from tests import future, make_db


class CharactersTest(unittest.TestCase):
    """Создание, изменение и удаление персонажей."""

    def setUp(self):
        """Создаёт БД с Мастером и Игроком."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        auth.register(self.conn, "Мастер", "gm", "1234", "1234", "GM")
        auth.register(self.conn, "Игрок", "pl", "1234", "1234", "PLAYER")
        self.gm = auth.login_user(self.conn, "gm", "1234")
        self.player = auth.login_user(self.conn, "pl", "1234")

    def add_character(self):
        """Создаёт тестового персонажа."""
        return characters.save_character(
            self.conn, self.player, "Пип", "Полурослик", "Плут", 4, ""
        )

    def test_create_and_edit(self):
        """Персонаж создаётся и изменяется."""
        char_id = self.add_character()
        characters.save_character(
            self.conn, self.player, "Пип", "Полурослик", "Плут", 5, "", char_id
        )
        self.assertEqual(characters.get_character(self.conn, char_id)["level"], 5)

    def test_empty_name_and_bad_level(self):
        """Пустое имя и уровень вне 1–20 не принимаются."""
        with self.assertRaises(ValidationError):
            characters.save_character(self.conn, self.player, "", "", "", 1, "")
        with self.assertRaises(ValidationError):
            characters.save_character(self.conn, self.player, "Пип", "", "", 21, "")

    def test_13_delete_with_active_signup(self):
        """Сценарий 13: персонажа с активной заявкой удалить нельзя."""
        char_id = self.add_character()
        game_id = games.save_game(self.conn, self.gm, "Игра", "", *future(), 4)
        signups.create_signup(self.conn, self.player, game_id, char_id)
        with self.assertRaises(ValidationError):
            characters.delete_character(self.conn, self.player, char_id)
        self.assertIsNotNone(characters.get_character(self.conn, char_id))

    def test_delete_without_signups(self):
        """Персонажа без активных заявок удалить можно."""
        char_id = self.add_character()
        characters.delete_character(self.conn, self.player, char_id)
        self.assertIsNone(characters.get_character(self.conn, char_id))


if __name__ == "__main__":
    unittest.main()
