"""Настройки программы на этом компьютере: тема и запомненные логины.

Хранятся в файле settings.json рядом с БД. Пароли сюда не записываются —
только логины для подсказки при входе.
"""

import json

from gm_hub.config import DB_PATH

SETTINGS_PATH = DB_PATH.parent / "settings.json"
MAX_LOGINS = 5  # сколько последних логинов подсказывать


def settings_file(path=None):
    """Возвращает путь к файлу настроек.

    Путь берётся в момент вызова, поэтому в тестах его можно подменить, не
    затрагивая настоящий settings.json.

    Args:
        path: Свой путь или None — тогда SETTINGS_PATH.
    """
    return SETTINGS_PATH if path is None else path


def read_settings(path=None) -> dict:
    """Читает все настройки.

    Args:
        path: Путь к settings.json (по умолчанию — файл рядом с БД).

    Returns:
        Словарь настроек (пустой, если файла нет или он испорчен).
    """
    try:
        with open(settings_file(path), encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_setting(key: str, value, path=None) -> None:
    """Меняет одну настройку, не трогая остальные.

    Args:
        key: Имя настройки, например «theme».
        value: Новое значение.
        path: Путь к settings.json.
    """
    data = read_settings(path)
    data[key] = value
    with open(settings_file(path), "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)


def get_setting(key: str, default=None, path=None):
    """Возвращает одну настройку (или default, если её ещё нет).

    Args:
        key: Имя настройки, например «large_text».
        default: Значение по умолчанию.
        path: Путь к settings.json.
    """
    return read_settings(path).get(key, default)


def recent_logins(path=None) -> list:
    """Возвращает логины, с которыми входили на этом компьютере (новые первыми)."""
    logins = read_settings(path).get("logins", [])
    return [login for login in logins if isinstance(login, str)][:MAX_LOGINS]


def remember_login(login: str, path=None) -> None:
    """Запоминает логин после успешного входа (он встаёт первым в списке).

    Args:
        login: Логин пользователя.
        path: Путь к settings.json.
    """
    login = login.strip()
    others = [x for x in recent_logins(path) if x.lower() != login.lower()]
    write_setting("logins", ([login] + others)[:MAX_LOGINS], path)


def forget_login(login: str, path=None) -> None:
    """Убирает логин из подсказок.

    Args:
        login: Логин пользователя.
        path: Путь к settings.json.
    """
    left = [x for x in recent_logins(path) if x.lower() != login.strip().lower()]
    write_setting("logins", left, path)


def matching_logins(typed: str, path=None) -> list:
    """Подсказки для введённого текста: логины, в которых он встречается.

    Args:
        typed: Что пользователь уже ввёл в поле «Логин».
        path: Путь к settings.json.

    Returns:
        Подходящие логины; полностью совпадающий логин не подсказывается.
    """
    typed = typed.strip().lower()
    return [x for x in recent_logins(path) if typed in x.lower() and x.lower() != typed]
