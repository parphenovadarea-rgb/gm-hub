"""Точка входа АС «GM Hub»: python main.py."""

import sys

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from gm_hub.db.database import connect, init_db
from gm_hub.ui import style
from gm_hub.ui.app import App


def main() -> None:
    """Открывает БД и запускает главное окно."""
    qt_app = QApplication(sys.argv)
    # Календарь и числа — по-русски, неделя начинается с понедельника.
    QLocale.setDefault(QLocale(QLocale.Russian, QLocale.Russia))
    style.apply(qt_app)
    conn = connect()
    init_db(conn)
    try:
        window = App(conn)
        sys.excepthook = window.show_error  # ошибки — в окне, а не в консоли
        window.show()
        qt_app.exec()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
