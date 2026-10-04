"""Подсистема «Авторизация»: регистрация и вход (п. 4.2.1 ТЗ)."""

import hashlib
import os

from gm_hub.config import now_str
from gm_hub.logic.errors import AccessError, ValidationError, require

ROLE_NAMES = {"GM": "Мастер", "PLAYER": "Игрок"}


def hash_password(password: str, salt: str | None = None) -> str:
    """Считает хэш пароля SHA-256 с солью (п. 4.1.9 ТЗ).

    Args:
        password: Пароль.
        salt: Соль. Если не передана, создаётся новая случайная.

    Returns:
        Строка «соль$хэш» для хранения в БД.
    """
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def check_password(password: str, stored: str) -> bool:
    """Сравнивает пароль с сохранённым хэшем.

    Args:
        password: Введённый пароль.
        stored: Строка «соль$хэш» из БД.

    Returns:
        True, если пароль верный.
    """
    salt = stored.split("$")[0]
    return hash_password(password, salt) == stored


def has_users(conn) -> bool:
    """Проверяет, есть ли в системе пользователи (сценарий 1 п. 6.1 ТЗ).

    Args:
        conn: Подключение к БД.

    Returns:
        True, если зарегистрирован хотя бы один пользователь.
    """
    return conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0] > 0


def register(conn, full_name, login, password, password2, role) -> int:
    """Регистрирует нового пользователя.

    Args:
        conn: Подключение к БД.
        full_name: ФИО.
        login: Логин.
        password: Пароль.
        password2: Повтор пароля.
        role: «GM» или «PLAYER».

    Returns:
        id нового пользователя.

    Raises:
        ValidationError: Если поле пустое, пароли не совпали или логин занят.
    """
    full_name = require(full_name, "ФИО")
    login = require(login, "Логин")
    require(password, "Пароль")
    if len(password) < 4:
        raise ValidationError("Пароль", "Пароль должен быть не короче 4 символов.")
    if password != password2:
        raise ValidationError("Повтор", "Пароли не совпадают.")
    if role not in ROLE_NAMES:
        raise ValidationError("Роль", "Выберите роль: Мастер или Игрок.")

    found = conn.execute("SELECT id FROM Users WHERE login = ?", (login,)).fetchone()
    if found:
        raise ValidationError("Логин", f"Логин «{login}» уже занят.")

    with conn:
        cur = conn.execute(
            "INSERT INTO Users (full_name, login, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (full_name, login, hash_password(password), role, now_str()),
        )
    return cur.lastrowid


def login_user(conn, login, password):
    """Выполняет вход по логину и паролю.

    Args:
        conn: Подключение к БД.
        login: Логин.
        password: Пароль.

    Returns:
        Строка таблицы Users (id, full_name, login, role, ...).

    Raises:
        ValidationError: Если поле пустое или логин/пароль неверные.
    """
    login = require(login, "Логин")
    require(password, "Пароль")
    user = conn.execute("SELECT * FROM Users WHERE login = ?", (login,)).fetchone()
    if user is None or not check_password(password, user["password_hash"]):
        raise ValidationError("Пароль", "Неверный логин или пароль.")
    return user


def check_gm(user) -> None:
    """Проверяет, что действие выполняет Мастер (п. 4.1.9 ТЗ).

    Args:
        user: Строка таблицы Users.

    Raises:
        AccessError: Если пользователь не Мастер.
    """
    if user["role"] != "GM":
        raise AccessError("Это действие доступно только Мастеру.")
