"""Тесты подсистемы «Расписание» (сценарий 4 п. 6.1 ТЗ)."""

import unittest

from gm_hub.logic import auth, games
from gm_hub.logic.errors import AccessError, ValidationError
from tests import future, make_db


class GamesTest(unittest.TestCase):
    """Создание и отмена сессий."""

    def setUp(self):
        """Создаёт БД с Мастером и Игроком."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        auth.register(self.conn, "Мастер", "gm", "1234", "1234", "GM")
        auth.register(self.conn, "Игрок", "pl", "1234", "1234", "PLAYER")
        self.gm = auth.login_user(self.conn, "gm", "1234")
        self.player = auth.login_user(self.conn, "pl", "1234")

    def test_04_new_game_has_4_free_seats(self):
        """Сценарий 4: сессия на 4 места видна в витрине со «Свободно: 4»."""
        games.save_game(self.conn, self.gm, "Шахта Эхо", "", *future(), 4)
        showcase = games.list_games(self.conn)
        self.assertEqual(len(showcase), 1)
        game = showcase[0]
        self.assertEqual(games.free_seats(game["max_players"], game["confirmed"]), 4)

    def test_max_players_must_be_positive(self):
        """Лимит мест — целое положительное число."""
        for bad in (0, -1, "abc"):
            with self.assertRaises(ValidationError):
                games.save_game(self.conn, self.gm, "Игра", "", *future(), bad)

    def test_date_in_past(self):
        """Дата сессии не может быть в прошлом."""
        with self.assertRaises(ValidationError):
            games.save_game(self.conn, self.gm, "Игра", "", "01.01.2020", "18:00", 4)

    def test_player_cannot_create_game(self):
        """Создавать сессии может только Мастер."""
        with self.assertRaises(AccessError):
            games.save_game(self.conn, self.player, "Игра", "", *future(), 4)

    def test_cancel_game(self):
        """Отменённая сессия пропадает из витрины."""
        game_id = games.save_game(self.conn, self.gm, "Игра", "", *future(), 4)
        games.cancel_game(self.conn, self.gm, game_id)
        self.assertEqual(games.list_games(self.conn), [])
        self.assertEqual(len(games.list_games(self.conn, "CANCELLED")), 1)


if __name__ == "__main__":
    unittest.main()
