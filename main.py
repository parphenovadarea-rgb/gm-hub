"""Точка входа АС «GM Hub»: python main.py."""

from gm_hub.db.database import connect, init_db
from gm_hub.ui.app import App


def main() -> None:
    """Открывает БД и запускает окно приложения."""
    conn = connect()
    init_db(conn)
    try:
        App(conn).mainloop()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
