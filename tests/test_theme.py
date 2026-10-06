"""Тесты сохранения выбранной темы оформления."""

import os
import tempfile
import unittest

from gm_hub.ui.theme import DARK, LIGHT, load_theme, save_theme


class ThemeTest(unittest.TestCase):
    """Тема запоминается в файле настроек."""

    def test_default_is_light(self):
        """Без файла настроек включается светлая тема."""
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(load_theme(os.path.join(folder, "settings.json")), "light")

    def test_save_and_load(self):
        """Сохранённая тёмная тема читается при следующем запуске."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "settings.json")
            save_theme("dark", path)
            self.assertEqual(load_theme(path), "dark")

    def test_palettes_have_same_colors(self):
        """В светлой и тёмной палитре одинаковый набор цветов."""
        self.assertEqual(set(LIGHT), set(DARK))


if __name__ == "__main__":
    unittest.main()
