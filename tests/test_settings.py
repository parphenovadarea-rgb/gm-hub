"""Тесты файла настроек: запомненные логины и тема."""

import os
import tempfile
import unittest

from gm_hub import settings
from gm_hub.ui.theme import load_theme, save_theme


class SettingsTest(unittest.TestCase):
    """Подсказки логинов при входе."""

    def setUp(self):
        """Создаёт временную папку для settings.json."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = os.path.join(folder.name, "settings.json")

    def test_last_login_first(self):
        """Последний вошедший логин стоит первым, повторов нет."""
        for login in ("агыг", "gleb", "агыг"):
            settings.remember_login(login, self.path)
        self.assertEqual(settings.recent_logins(self.path), ["агыг", "gleb"])

    def test_only_five_logins(self):
        """Запоминаются только 5 последних логинов."""
        for number in range(7):
            settings.remember_login(f"user{number}", self.path)
        self.assertEqual(len(settings.recent_logins(self.path)), 5)
        self.assertEqual(settings.recent_logins(self.path)[0], "user6")

    def test_matching_and_forget(self):
        """Подсказка по части логина; удалённый логин больше не подсказывается."""
        settings.remember_login("gleb", self.path)
        settings.remember_login("polina", self.path)
        self.assertEqual(settings.matching_logins("GL", self.path), ["gleb"])
        self.assertEqual(settings.matching_logins("gleb", self.path), [])
        settings.forget_login("gleb", self.path)
        self.assertEqual(settings.recent_logins(self.path), ["polina"])

    def test_theme_keeps_logins(self):
        """Смена темы не стирает запомненные логины."""
        settings.remember_login("gleb", self.path)
        save_theme("dark", self.path)
        self.assertEqual(load_theme(self.path), "dark")
        self.assertEqual(settings.recent_logins(self.path), ["gleb"])


if __name__ == "__main__":
    unittest.main()
