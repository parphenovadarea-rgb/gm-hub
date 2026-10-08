"""Тесты календаря месяца и настроек вида."""

import os
import tempfile
import unittest
from datetime import date

from gm_hub import settings
from gm_hub.logic import month


class MonthTest(unittest.TestCase):
    """Сетка дней для календаря."""

    def test_october_2026_starts_on_thursday(self):
        """1 октября 2026 — четверг: первые три клетки недели пустые."""
        weeks = month.month_grid(2026, 10)
        self.assertEqual(weeks[0][:4], [None, None, None, date(2026, 10, 1)])
        days = [d for week in weeks for d in week if d]
        self.assertEqual(len(days), 31)
        self.assertTrue(all(len(week) == 7 for week in weeks))

    def test_shift_month_over_year(self):
        """После декабря — январь следующего года, и наоборот."""
        self.assertEqual(month.shift_month(2026, 12, 1), (2027, 1))
        self.assertEqual(month.shift_month(2026, 1, -1), (2025, 12))

    def test_games_by_day(self):
        """Сессии раскладываются по дням и сортируются по времени."""
        games = [
            {"title": "Б", "scheduled_at": "2026-10-11 18:00"},
            {"title": "А", "scheduled_at": "2026-10-11 12:00"},
            {"title": "В", "scheduled_at": "2026-10-12 18:00"},
        ]
        days = month.games_by_day(games)
        self.assertEqual([g["title"] for g in days[date(2026, 10, 11)]], ["А", "Б"])
        self.assertEqual(month.title(2026, 10), "Октябрь 2026")


class ViewSettingsTest(unittest.TestCase):
    """Настройки вида сохраняются в settings.json."""

    def test_get_setting_default_and_saved(self):
        """Без файла — значение по умолчанию, после записи — сохранённое."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "settings.json")
            self.assertEqual(settings.get_setting("tab_GM", 0, path), 0)
            settings.write_setting("tab_GM", 3, path)
            settings.write_setting("large_text", True, path)
            self.assertEqual(settings.get_setting("tab_GM", 0, path), 3)
            self.assertTrue(settings.get_setting("large_text", False, path))


if __name__ == "__main__":
    unittest.main()
