"""Тесты по сценариям п. 6.1 ТЗ."""

from datetime import datetime, timedelta

from gm_hub.config import SHOW_FORMAT
from gm_hub.db.database import connect, init_db


def make_db():
    """Создаёт пустую БД в памяти для теста.

    Returns:
        Подключение к новой БД.
    """
    conn = connect(":memory:")
    init_db(conn)
    return conn


def future(days: int = 7) -> tuple[str, str]:
    """Возвращает дату и время в будущем в формате окна.

    Args:
        days: Через сколько дней.

    Returns:
        Пара (дата «ДД.ММ.ГГГГ», время «ЧЧ:ММ»).
    """
    text = (datetime.now() + timedelta(days=days)).strftime(SHOW_FORMAT)
    return text[:10], "18:00"
