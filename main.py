"""Точка входа АС «GM Hub»: python main.py."""

import importlib

from gm_hub.db.database import connect, init_db
from gm_hub.ui.app import make_dpi_aware


def load_ui():
    """Загружает (или перезагружает) модули окон и возвращает класс App.

    При смене темы цвета берутся заново из theme.py, поэтому модули
    интерфейса перечитываются в порядке их зависимостей.
    """
    names = [
        "theme",
        "common",
        "table",
        "auth_windows",
        "profile_window",
        "gm_window",
        "player_window",
        "help_window",
        "app",
    ]
    module = None
    for name in names:
        module = importlib.reload(importlib.import_module("gm_hub.ui." + name))
    return module.App


def main() -> None:
    """Открывает БД и запускает окно; после смены темы окно создаётся заново."""
    make_dpi_aware()
    conn = connect()
    init_db(conn)
    user = None
    try:
        while True:
            app = load_ui()(conn, user)
            app.mainloop()
            if not app.restart:
                break
            user = app.user  # после смены темы остаёмся в своём кабинете
    finally:
        conn.close()


if __name__ == "__main__":
    main()
