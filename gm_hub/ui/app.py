"""Главное окно приложения: переключает экраны входа, регистрации и кабинетов."""

import ctypes
import sqlite3
import tkinter as tk
import traceback
from tkinter import messagebox

from gm_hub.logic import auth
from gm_hub.logic.errors import AccessError, ValidationError
from gm_hub.ui.auth_windows import LoginFrame, RegisterFrame
from gm_hub.ui.common import ScrollArea, fix_corners, px, setup_style
from gm_hub.ui.gm_window import GMFrame
from gm_hub.ui.player_window import PlayerFrame
from gm_hub.ui.profile_window import ProfileWindow
from gm_hub.ui.theme import THEME, save_theme


def make_dpi_aware() -> None:
    """Сообщает Windows, что программа сама учитывает масштаб экрана.

    Без этого при масштабе 125–150 % Windows растягивает окно как картинку
    и текст получается размытым. Вызывать до создания окна.
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass  # не Windows или старая Windows — оставляем как есть


class App(tk.Tk):
    """Приложение GM Hub.

    Attributes:
        conn: Подключение к БД.
        user: Вошедший пользователь или None.
    """

    def __init__(self, conn, user=None):
        """Открывает регистрацию при первом запуске, иначе окно входа.

        Args:
            conn: Подключение к БД.
            user: Пользователь, если окно пересоздаётся после смены темы.
        """
        super().__init__()
        self.conn = conn
        self.user = None
        self.screen = None
        self.restart = False  # True — main.py пересоздаст окно с новой темой
        setup_style(self)
        # Экраны кладутся в область с ползунками: в маленьком окне их можно
        # прокрутить, а не обрезать.
        self.scroll = ScrollArea(self)
        self.scroll.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        if user is not None:
            self.open_main(user)
        # Сценарий 1 п. 6.1 ТЗ: при первом запуске открывается регистрация.
        elif auth.has_users(conn):
            self.show_login()
        else:
            self.show_register()

    def show(
        self, screen_class, title: str, size: str, min_size: str, card_width=None
    ) -> None:
        """Заменяет текущий экран новым.

        Args:
            screen_class: Класс экрана (Frame), создаётся здесь.
            title: Заголовок окна.
            size: Размер окна при открытии, например «1280x760».
            min_size: Размер, меньше которого экран не сжимается: если окно
                уменьшить сильнее, появляются ползунки.
            card_width: Для входа и регистрации — ширина карточки с формой.
                Карточка стоит по центру окна и не растягивается, даже если
                окно развернуть на весь экран. None — экран на всё окно.
        """
        if self.screen is not None:
            self.screen.destroy()
        self.title(f"Game Master Hub — {title}")
        width, height = (int(n) for n in size.split("x"))
        self.geometry(f"{px(width)}x{px(height)}")
        page = self.scroll.page
        page.configure(style="Page.TFrame" if card_width else "TFrame")
        self.screen = screen_class(self)
        if card_width:
            self.screen.configure(style="Card.TFrame")
            self.screen.place(relx=0.5, rely=0.5, anchor="center", width=px(card_width))
            fix_corners(page)  # уголки карточки — цвета фона страницы
        else:
            self.screen.pack(fill="both", expand=True)
        min_width, min_height = (int(n) for n in min_size.split("x"))
        self.scroll.set_min_size(px(min_width), px(min_height))

    def show_login(self) -> None:
        """Открывает окно входа."""
        self.show(LoginFrame, "Вход", "520x500", "480x460", card_width=440)

    def show_register(self) -> None:
        """Открывает окно регистрации."""
        self.show(RegisterFrame, "Регистрация", "580x680", "540x640", card_width=500)

    def open_main(self, user) -> None:
        """Открывает окно по роли пользователя (п. 4.2.1 ТЗ).

        Args:
            user: Вошедший пользователь.
        """
        self.user = user
        if user["role"] == "GM":
            self.show(GMFrame, "Мастер", "1360x780", "1360x640")
        else:
            self.show(PlayerFrame, "Игрок", "1420x780", "1240x640")

    def toggle_theme(self) -> None:
        """Переключает светлую и тёмную тему.

        Цвета задаются при создании виджетов, поэтому окно закрывается,
        а main.py создаёт его заново уже с новой темой (вход не нужен).
        """
        if not self.can_leave():
            return
        save_theme("light" if THEME == "dark" else "dark")
        self.restart = True
        self.destroy()

    def can_leave(self) -> bool:
        """Спрашивает о несохранённых изменениях на открытом экране.

        Returns:
            True, если экран можно закрыть.
        """
        return getattr(self.screen, "can_leave", lambda: True)()

    def on_close(self) -> None:
        """Закрывает программу (крестик окна), не теряя несохранённое."""
        if self.can_leave():
            self.destroy()

    def show_profile(self) -> None:
        """Открывает окно профиля текущего пользователя."""
        ProfileWindow(self)

    def logout(self) -> None:
        """Выходит из учётной записи."""
        if not self.can_leave():
            return
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
