"""Тесты ввода даты и времени по маске."""

import unittest

from gm_hub.ui.mask import DATE_MASK, TIME_MASK, apply_mask


class MaskTest(unittest.TestCase):
    """Точки и двоеточие ставятся автоматически."""

    def test_date(self):
        """Из цифр получается дата ДД.ММ.ГГГГ."""
        self.assertEqual(apply_mask("27092026", DATE_MASK), "27.09.2026")

    def test_time(self):
        """Из цифр получается время ЧЧ:ММ."""
        self.assertEqual(apply_mask("1800", TIME_MASK), "18:00")

    def test_partial_input(self):
        """Разделитель появляется только перед следующей цифрой."""
        self.assertEqual(apply_mask("27", DATE_MASK), "27")
        self.assertEqual(apply_mask("270", DATE_MASK), "27.0")

    def test_letters_and_extra_digits_ignored(self):
        """Буквы отбрасываются, лишние цифры не помещаются."""
        self.assertEqual(apply_mask("1а8:0099", TIME_MASK), "18:00")


if __name__ == "__main__":
    unittest.main()
