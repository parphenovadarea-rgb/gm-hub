"""Тесты подсистемы «Сюжетный блокнот» (сценарии 11–12 п. 6.1 ТЗ)."""

import unittest

from gm_hub.logic import auth, games, notes
from gm_hub.logic.errors import AccessError, ValidationError
from tests import future, make_db


class NotesTest(unittest.TestCase):
    """Заметки к сессиям и база мира."""

    def setUp(self):
        """Создаёт Мастера, Игрока и две сессии."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        auth.register(self.conn, "Мастер", "gm", "1234", "1234", "GM")
        auth.register(self.conn, "Игрок", "pl", "1234", "1234", "PLAYER")
        self.gm = auth.login_user(self.conn, "gm", "1234")
        self.player = auth.login_user(self.conn, "pl", "1234")
        self.game1 = games.save_game(self.conn, self.gm, "Игра 1", "", *future(), 4)
        self.game2 = games.save_game(self.conn, self.gm, "Игра 2", "", *future(8), 4)

    def test_11_note_belongs_to_game(self):
        """Сценарий 11: у сессии отображается именно её заметка."""
        notes.save_game_note(self.conn, self.gm, self.game1, "Сцена 1. Обвал")
        notes.save_game_note(self.conn, self.gm, self.game2, "Сцена 1. Порт")
        note = notes.get_game_note(self.conn, self.gm, self.game1)
        self.assertEqual(note["content"], "Сцена 1. Обвал")
        self.assertIsNotNone(note["updated_at"])
        notes.delete_game_note(self.conn, self.gm, self.game1)
        self.assertIsNone(notes.get_game_note(self.conn, self.gm, self.game1))

    def test_12_player_has_no_access(self):
        """Сценарий 12: Игроку блокнот и база мира недоступны."""
        with self.assertRaises(AccessError):
            notes.get_game_note(self.conn, self.player, self.game1)
        with self.assertRaises(AccessError):
            notes.list_world_notes(self.conn, self.player)

    def test_world_notes(self):
        """Записи базы мира создаются и фильтруются по категории."""
        notes.save_world_note(self.conn, self.gm, "NPC", "Мэтр Олдрик", "трактирщик")
        notes.save_world_note(self.conn, self.gm, "LORE", "Шахта Эхо", "")
        self.assertEqual(len(notes.list_world_notes(self.conn, self.gm, "NPC")), 1)
        with self.assertRaises(ValidationError):
            notes.save_world_note(self.conn, self.gm, "NPC", "", "")


if __name__ == "__main__":
    unittest.main()
