"""Тесты подсистемы «Авторизация» (сценарии 1–3 п. 6.1 ТЗ)."""

import unittest

from gm_hub.logic import auth
from gm_hub.logic.errors import ValidationError
from tests import make_db


class AuthTest(unittest.TestCase):
    """Регистрация и вход."""

    def setUp(self):
        """Создаёт пустую БД."""
        self.conn = make_db()
        self.addCleanup(self.conn.close)

    def test_01_first_start_has_no_users(self):
        """Сценарий 1: при первом запуске пользователей нет — открыть регистрацию."""
        self.assertFalse(auth.has_users(self.conn))

    def test_02_empty_login(self):
        """Сценарий 2: пустой логин — ошибка, данные не сохраняются."""
        with self.assertRaises(ValidationError) as ctx:
            auth.register(self.conn, "Иванов И. И.", "  ", "1234", "1234", "GM")
        self.assertEqual(ctx.exception.field, "Логин")
        self.assertFalse(auth.has_users(self.conn))

    def test_03_duplicate_login(self):
        """Сценарий 3: занятый логин — ошибка, дубль не создаётся."""
        auth.register(self.conn, "Иванов И. И.", "ivan", "1234", "1234", "GM")
        with self.assertRaises(ValidationError):
            auth.register(self.conn, "Петров П. П.", "ivan", "5678", "5678", "PLAYER")
        count = self.conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0]
        self.assertEqual(count, 1)

    def test_passwords_must_match(self):
        """Пароль и повтор должны совпадать."""
        with self.assertRaises(ValidationError):
            auth.register(self.conn, "Иванов И. И.", "ivan", "1234", "4321", "GM")

    def test_password_is_hashed(self):
        """Пароль хранится только в виде хэша с солью."""
        auth.register(self.conn, "Иванов И. И.", "ivan", "secret", "secret", "GM")
        stored = self.conn.execute("SELECT password_hash FROM Users").fetchone()[0]
        self.assertNotIn("secret", stored)
        self.assertIn("$", stored)

    def test_login(self):
        """Вход с верным паролем проходит, с неверным — нет."""
        auth.register(self.conn, "Иванов И. И.", "ivan", "1234", "1234", "GM")
        user = auth.login_user(self.conn, "ivan", "1234")
        self.assertEqual(user["role"], "GM")
        with self.assertRaises(ValidationError):
            auth.login_user(self.conn, "ivan", "0000")

    def test_update_profile(self):
        """ФИО и пароль меняются только при верном текущем пароле."""
        auth.register(self.conn, "Иванов И. И.", "ivan", "1234", "1234", "GM")
        user = auth.login_user(self.conn, "ivan", "1234")
        with self.assertRaises(ValidationError):
            auth.update_profile(self.conn, user, "Иванов И. П.", "0000")
        user = auth.update_profile(
            self.conn, user, "Иванов И. П.", "1234", "5678", "5678"
        )
        self.assertEqual(user["full_name"], "Иванов И. П.")
        auth.login_user(self.conn, "ivan", "5678")

    def test_delete_account(self):
        """Аккаунт без персонажей и сессий удаляется."""
        auth.register(self.conn, "Иванов И. И.", "ivan", "1234", "1234", "PLAYER")
        user = auth.login_user(self.conn, "ivan", "1234")
        auth.delete_account(self.conn, user, "1234")
        self.assertFalse(auth.has_users(self.conn))


if __name__ == "__main__":
    unittest.main()
