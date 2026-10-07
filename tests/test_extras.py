"""Тесты доработок: новые решения, список участников, фильтр витрины по дате."""

import csv
import os
import tempfile
import unittest
from datetime import datetime

from gm_hub.logic import auth, characters, games, signups
from gm_hub.logic.errors import AccessError
from tests import future, make_db


class ExtrasTest(unittest.TestCase):
    """Отметка новых решений и сохранение состава сессии."""

    def setUp(self):
        """Создаёт Мастера, Игрока с персонажем и сессию с заявкой."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)
        auth.register(self.conn, "Мастер", "gm", "1234", "1234", "GM")
        auth.register(self.conn, "Другой Мастер", "gm2", "1234", "1234", "GM")
        auth.register(self.conn, "Глеб Денисов", "pl", "1234", "1234", "PLAYER")
        self.gm = auth.login_user(self.conn, "gm", "1234")
        self.gm2 = auth.login_user(self.conn, "gm2", "1234")
        self.player = auth.login_user(self.conn, "pl", "1234")
        char = characters.save_character(
            self.conn, self.player, "Пип", "Полурослик", "Плут", 4, ""
        )
        self.game = games.save_game(self.conn, self.gm, "Шахта Эхо", "", *future(), 4)
        self.signup = signups.create_signup(
            self.conn, self.player, self.game, char, "Приду к 18:15"
        )

    def test_new_decision_is_counted(self):
        """Решение Мастера считается новым, пока Игрок не открыл «Мои записи»."""
        self.assertEqual(signups.count_new_decisions(self.conn, self.player), 0)
        signups.confirm_signup(self.conn, self.gm, self.signup)
        # время решения — в прошлом, чтобы оно было раньше «просмотра»
        with self.conn:
            self.conn.execute("UPDATE Game_Signups SET decided_at = '2026-01-01 10:00'")
        self.assertEqual(signups.count_new_decisions(self.conn, self.player), 1)
        signups.mark_decisions_seen(self.conn, self.player)
        self.assertEqual(signups.count_new_decisions(self.conn, self.player), 0)

    def test_export_participants(self):
        """В файл попадают только подтверждённые участники сессии."""
        signups.confirm_signup(self.conn, self.gm, self.signup)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "состав.csv")
            count = signups.export_participants(self.conn, self.gm, self.game, path)
            with open(path, encoding="utf-8-sig") as file:
                rows = list(csv.reader(file, delimiter=";"))
        self.assertEqual(count, 1)
        self.assertEqual(rows[0][0], "Сессия: Шахта Эхо")
        self.assertEqual(
            rows[2][:5], ["Пип", "Полурослик", "Плут", "4", "Глеб Денисов"]
        )

    def test_export_other_master_game(self):
        """Состав чужой сессии сохранить нельзя."""
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(AccessError):
                signups.export_participants(
                    self.conn, self.gm2, self.game, os.path.join(folder, "x.csv")
                )


class PeriodTest(unittest.TestCase):
    """Фильтр витрины по дате."""

    NOW = datetime(2026, 10, 7, 12, 0)

    def test_all_dates(self):
        """«Все даты» пропускают любую сессию."""
        self.assertTrue(games.in_period("2027-05-01 18:00", None, self.NOW))

    def test_week(self):
        """«7 дней»: через 3 дня — да, через 10 дней — нет."""
        self.assertTrue(games.in_period("2026-10-10 18:00", 7, self.NOW))
        self.assertFalse(games.in_period("2026-10-17 18:00", 7, self.NOW))


if __name__ == "__main__":
    unittest.main()
