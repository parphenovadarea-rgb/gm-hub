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


def check_new_password(password: str, password2: str) -> None:
    """Проверяет новый пароль и его повтор.

    Args:
        password: Пароль.
        password2: Повтор пароля.

    Raises:
        ValidationError: Если пароль пустой, короткий или не совпал с повтором.
    """
    require(password, "Пароль")
    if len(password) < 4:
        raise ValidationError("Пароль", "Пароль должен быть не короче 4 символов.")
    if password != password2:
        raise ValidationError("Повтор", "Пароли не совпадают.")


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
    check_new_password(password, password2)
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


def update_profile(conn, user, full_name, password, new_password="", new_password2=""):
    """Изменяет ФИО и, если нужно, пароль пользователя.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.
        full_name: Новое ФИО.
        password: Текущий пароль для подтверждения.
        new_password: Новый пароль. Пустой — пароль не меняется.
        new_password2: Повтор нового пароля.

    Returns:
        Обновлённая строка таблицы Users.

    Raises:
        ValidationError: Если ФИО пустое, текущий пароль неверный
            или новый пароль не прошёл проверку.
    """
    full_name = require(full_name, "ФИО")
    check_current_password(conn, user, password)
    change_password = bool(new_password or new_password2)
    if change_password:
        check_new_password(new_password, new_password2)
    with conn:
        conn.execute(
            "UPDATE Users SET full_name = ? WHERE id = ?", (full_name, user["id"])
        )
        if change_password:
            conn.execute(
                "UPDATE Users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user["id"]),
            )
    return conn.execute("SELECT * FROM Users WHERE id = ?", (user["id"],)).fetchone()


def delete_account(conn, user, password) -> None:
    """Удаляет аккаунт, если у пользователя нет персонажей и сессий.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.
        password: Текущий пароль для подтверждения.

    Raises:
        ValidationError: Если пароль неверный или у пользователя есть данные.
    """
    check_current_password(conn, user, password)
    characters = conn.execute(
        "SELECT COUNT(*) FROM Characters WHERE user_id = ?", (user["id"],)
    ).fetchone()[0]
    games = conn.execute(
        "SELECT COUNT(*) FROM Games WHERE gm_id = ?", (user["id"],)
    ).fetchone()[0]
    if characters or games:
        raise ValidationError(
            "Аккаунт",
            "Аккаунт нельзя удалить, пока у вас есть персонажи или сессии. "
            "Сначала удалите их.",
        )
    with conn:
        conn.execute("DELETE FROM Users WHERE id = ?", (user["id"],))


def check_current_password(conn, user, password) -> None:
    """Проверяет текущий пароль перед изменением аккаунта.

    Args:
        conn: Подключение к БД.
        user: Текущий пользователь.
        password: Введённый пароль.

    Raises:
        ValidationError: Если пароль неверный.
    """
    stored = conn.execute(
        "SELECT password_hash FROM Users WHERE id = ?", (user["id"],)
    ).fetchone()[0]
    if not check_password(password or "", stored):
        raise ValidationError("Текущий пароль", "Текущий пароль введён неверно.")


def check_gm(user) -> None:
    """Проверяет, что действие выполняет Мастер (п. 4.1.9 ТЗ).

    Args:
        user: Строка таблицы Users.

    Raises:
        AccessError: Если пользователь не Мастер.
    """
    if user["role"] != "GM":
        raise AccessError("Это действие доступно только Мастеру.")
