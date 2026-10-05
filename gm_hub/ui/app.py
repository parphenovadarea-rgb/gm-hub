"""Главное окно приложения: переключает экраны входа, регистрации и кабинетов."""

import sqlite3
import tkinter as tk
import traceback
from tkinter import messagebox

from gm_hub.logic import auth
from gm_hub.logic.errors import AccessError, ValidationError
from gm_hub.ui.auth_windows import LoginFrame, RegisterFrame
from gm_hub.ui.common import setup_style
from gm_hub.ui.gm_window import GMFrame
from gm_hub.ui.player_window import PlayerFrame
from gm_hub.ui.profile_window import ProfileWindow


class App(tk.Tk):
    """Приложение GM Hub.

    Attributes:
        conn: Подключение к БД.
        user: Вошедший пользователь или None.
    """

    def __init__(self, conn):
        """Открывает регистрацию при первом запуске, иначе окно входа.

        Args:
            conn: Подключение к БД.
        """
        super().__init__()
        self.conn = conn
        self.user = None
        self.screen = None
        setup_style(self)
        # Сценарий 1 п. 6.1 ТЗ: при первом запуске открывается регистрация.
        if auth.has_users(conn):
            self.show_login()
        else:
            self.show_register()

    def show(self, screen_class, title: str, size: str) -> None:
        """Заменяет текущий экран новым.

        Args:
            screen_class: Класс экрана (Frame), создаётся здесь.
            title: Заголовок окна.
            size: Размер окна, например «1280x760».
        """
        if self.screen is not None:
            self.screen.destroy()
        self.title(f"Game Master Hub — {title}")
        self.geometry(size)
        self.screen = screen_class(self)
        self.screen.pack(fill="both", expand=True)

    def show_login(self) -> None:
        """Открывает окно входа."""
        self.show(LoginFrame, "Вход", "470x430")

    def show_register(self) -> None:
        """Открывает окно регистрации."""
        self.show(RegisterFrame, "Регистрация", "500x570")

    def open_main(self, user) -> None:
        """Открывает окно по роли пользователя (п. 4.2.1 ТЗ).

        Args:
            user: Вошедший пользователь.
        """
        self.user = user
        if user["role"] == "GM":
            self.show(GMFrame, "Мастер", "1240x700")
        else:
            self.show(PlayerFrame, "Игрок", "1300x700")

    def show_profile(self) -> None:
        """Открывает окно профиля текущего пользователя."""
        ProfileWindow(self)

    def logout(self) -> None:
        """Выходит из учётной записи."""
        self.user = None
        self.show_login()

    def report_callback_exception(self, exc_type, exc, tb) -> None:
        """Показывает любую ошибку в окне сообщения вместо аварийного завершения.

        Tkinter вызывает этот метод, если в обработчике кнопки возникло
        исключение (п. 4.1.4 ТЗ: программа продолжает работу).

        Args:
            exc_type: Класс исключения.
            exc: Исключение.
            tb: Трассировка.
        """
        if isinstance(exc, ValidationError):
            messagebox.showwarning("Проверьте данные", exc.message)
        elif isinstance(exc, AccessError):
            messagebox.showerror("Доступ запрещён", str(exc))
        elif isinstance(exc, sqlite3.Error):
            messagebox.showerror("Ошибка базы данных", f"Операция не выполнена: {exc}")
        else:
            traceback.print_exception(exc_type, exc, tb)
            messagebox.showerror("Ошибка", f"Непредвиденная ошибка: {exc}")
