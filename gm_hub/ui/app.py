"""Главное окно приложения: переключает экраны входа, регистрации и кабинетов."""

import sqlite3
import traceback

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QApplication, QFrame, QMainWindow, QScrollArea

from gm_hub.logic import auth
from gm_hub.logic.errors import AccessError, ValidationError
from gm_hub.settings import get_setting, write_setting
from gm_hub.ui import style, theme
from gm_hub.ui.auth_windows import LoginFrame, RegisterFrame
from gm_hub.ui.common import hbox, info, vbox
from gm_hub.ui.gm_window import GMFrame
from gm_hub.ui.help_window import HelpWindow
from gm_hub.ui.player_window import PlayerFrame
from gm_hub.ui.profile_window import ProfileWindow


class App(QMainWindow):
    """Приложение GM Hub.

    Attributes:
        conn: Подключение к БД.
        user: Вошедший пользователь или None.
        screen: Открытый экран (вход, регистрация или кабинет).
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
        self.window_key = None  # имя настройки с размером окна открытого кабинета
        self.help = None
        # Экраны кладутся в область с ползунками: в маленьком окне их можно
        # прокрутить, а не обрезать.
        self.scroll = QScrollArea()
        self.scroll.setObjectName("main")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.setCentralWidget(self.scroll)
        # Сценарий 1 п. 6.1 ТЗ: при первом запуске открывается регистрация.
        if auth.has_users(conn):
            self.show_login()
        else:
            self.show_register()

    def show_screen(
        self, screen_class, title: str, size, min_size, card_width=None
    ) -> None:
        """Заменяет текущий экран новым.

        Args:
            screen_class: Класс экрана, создаётся здесь.
            title: Заголовок окна.
            size: Размер окна при открытии (ширина, высота).
            min_size: Размер, меньше которого экран не сжимается: если окно
                уменьшить сильнее, появляются ползунки.
            card_width: Для входа и регистрации — ширина карточки с формой.
                Карточка стоит по центру окна и не растягивается, даже если
                окно развернуть на весь экран. None — экран на всё окно.
        """
        self.save_window()
        self.setWindowTitle(f"Game Master Hub — {title}")
        if self.isMaximized():
            self.showNormal()
        self.resize(*size)
        self.screen = screen_class(self)
        if card_width:
            page = QFrame()
            page.setObjectName("page")
            column = vbox(page, margins=20)
            row = hbox()
            row.addStretch()
            self.screen.setFixedWidth(card_width)
            row.addWidget(self.screen)
            row.addStretch()
            column.addStretch()
            column.addLayout(row)
            column.addStretch()
            widget = page
        else:
            widget = self.screen
        widget.setMinimumSize(*min_size)
        old = self.scroll.takeWidget()
        self.scroll.setWidget(widget)
        if old is not None:
            old.deleteLater()

    def show_login(self) -> None:
        """Открывает окно входа."""
        self.show_screen(LoginFrame, "Вход", (520, 520), (480, 470), card_width=440)

    def show_register(self) -> None:
        """Открывает окно регистрации."""
        self.show_screen(
            RegisterFrame, "Регистрация", (600, 700), (560, 660), card_width=500
        )

    def open_main(self, user) -> None:
        """Открывает окно по роли пользователя (п. 4.2.1 ТЗ).

        Args:
            user: Вошедший пользователь.
        """
        self.user = user
        if user["role"] == "GM":
            self.show_screen(GMFrame, "Мастер", (1360, 780), (1280, 620))
        else:
            self.show_screen(PlayerFrame, "Игрок", (1420, 780), (1240, 620))
        # Размер и положение окна кабинета — как в прошлый раз.
        self.window_key = "window_" + user["role"]
        saved = get_setting(self.window_key)
        if isinstance(saved, str):
            self.restoreGeometry(QByteArray.fromBase64(saved.encode()))

    def save_window(self) -> None:
        """Запоминает размер и положение окна кабинета перед его закрытием."""
        if self.window_key is None:
            return
        value = bytes(self.saveGeometry().toBase64()).decode()
        try:
            write_setting(self.window_key, value)
        except OSError:
            pass  # файл настроек недоступен — окно откроется обычного размера
        self.window_key = None

    def reopen(self) -> None:
        """Перерисовывает открытый кабинет (после смены темы или шрифта)."""
        style.apply(QApplication.instance())
        if self.user is not None:
            self.open_main(self.user)

    def is_dark(self) -> bool:
        """Включена ли тёмная тема."""
        return theme.THEME == "dark"

    def toggle_theme(self) -> None:
        """Переключает светлую и тёмную тему."""
        if not self.can_leave():
            return
        new = "light" if self.is_dark() else "dark"
        try:
            theme.save_theme(new)
        except OSError:
            pass  # тема включится, но не запомнится
        theme.set_theme(new)
        self.reopen()

    def set_large_text(self, on: bool) -> None:
        """Включает или выключает крупный текст (настройка в «Профиле»)."""
        if not self.can_leave():
            return
        write_setting("large_text", bool(on))
        self.reopen()

    def show_help(self) -> None:
        """Открывает справку по роли пользователя (F1)."""
        if self.help is not None:
            self.help.close()
        self.help = HelpWindow(self, self.user["role"] if self.user else "PLAYER")
        self.help.show()

    def can_leave(self) -> bool:
        """Спрашивает о несохранённых изменениях на открытом экране.

        Returns:
            True, если экран можно закрыть.
        """
        return getattr(self.screen, "can_leave", lambda: True)()

    def closeEvent(self, event):
        """Закрывает программу (крестик окна), не теряя несохранённое."""
        if self.can_leave():
            self.save_window()
            event.accept()
        else:
            event.ignore()

    def show_profile(self) -> None:
        """Открывает окно профиля текущего пользователя."""
        ProfileWindow(self).exec()

    def logout(self) -> None:
        """Выходит из учётной записи."""
        if not self.can_leave():
            return
        self.user = None
        self.show_login()

    def show_error(self, exc_type, exc, tb) -> None:
        """Показывает любую ошибку в окне сообщения вместо аварийного завершения.

        Qt вызывает этот метод (через sys.excepthook), если в обработчике
        кнопки возникло исключение (п. 4.1.4 ТЗ: программа продолжает работу).

        Args:
            exc_type: Класс исключения.
            exc: Исключение.
            tb: Трассировка.
        """
        parent = QApplication.activeWindow() or self
        if isinstance(exc, ValidationError):
            info(parent, "Проверьте данные", exc.message)
        elif isinstance(exc, AccessError):
            info(parent, "Доступ запрещён", str(exc))
        elif isinstance(exc, sqlite3.Error):
            info(parent, "Ошибка базы данных", f"Операция не выполнена: {exc}")
        else:
            traceback.print_exception(exc_type, exc, tb)
            info(parent, "Ошибка", f"Непредвиденная ошибка: {exc}")
