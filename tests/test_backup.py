"""Тест резервного копирования БД (п. 4.1.8 ТЗ)."""

import sqlite3
import tempfile
import unittest

from gm_hub.db.database import backup_db
from gm_hub.logic import auth
from tests import make_db


class BackupTest(unittest.TestCase):
    """Копия БД содержит те же данные."""

    def test_backup_copies_data(self):
        """В копии есть зарегистрированный пользователь."""
        conn = make_db()
        self.addCleanup(conn.close)
        auth.register(conn, "Мастер", "gm", "1234", "1234", "GM")
        with tempfile.TemporaryDirectory() as folder:
            path = backup_db(conn, folder)
            copy = sqlite3.connect(path)
            logins = [row[0] for row in copy.execute("SELECT login FROM Users")]
            copy.close()
        self.assertEqual(logins, ["gm"])


if __name__ == "__main__":
    unittest.main()
