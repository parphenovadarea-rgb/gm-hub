"""Окна «Вход» и «Регистрация» (макеты 01 и 02)."""

import tkinter as tk
from tkinter import ttk

from gm_hub import settings
from gm_hub.logic import auth
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    BG,
    FONT,
    INK,
    LINE,
    MUTED,
    Banner,
    ChoiceCards,
    field,
    link,
    password_field,
    px,
)
from gm_hub.ui.theme import COLORS

ROLES = [
    ("GM", "Мастер", "создаю сессии, веду сюжет"),
    ("PLAYER", "Игрок", "веду персонажей, записываюсь"),
]


class LoginHints:
    """Подсказки логинов под полем «Логин», как в браузере.

    Показывает логины, с которыми уже входили на этом компьютере. Выбрать —
    щелчком или стрелками и Enter; крестик убирает логин из подсказок.
    """

    def __init__(self, entry, on_pick):
        """Создаёт выпадающий список (пока скрытый).

        Args:
            entry: Поле «Логин».
            on_pick: Что сделать после выбора логина (перейти к паролю).
        """
        self.entry = entry
        self.on_pick = on_pick
        self.items = []  # подсказанные логины
        self.current = -1  # выбранная стрелками строка
        # Рамка 1 px цвета линии, внутри — строки подсказок.
        self.box = tk.Frame(entry.master, bg=LINE, padx=1, pady=1)
        entry.bind("<KeyRelease>", self.on_key)
        entry.bind("<Button-1>", lambda e: self.show())
        entry.bind("<Down>", lambda e: self.move(1))
        entry.bind("<Up>", lambda e: self.move(-1))
        entry.bind("<Escape>", lambda e: self.hide())
        entry.bind("<FocusOut>", lambda e: self.hide())

    def on_key(self, event) -> None:
        """После ввода символа обновляет подсказки."""
        if event.keysym not in ("Up", "Down", "Return", "Escape", "Tab"):
            self.show()

    def show(self) -> None:
        """Показывает логины, подходящие под введённый текст."""
        self.items = settings.matching_logins(self.entry.get())
        self.current = -1
        for row in self.box.winfo_children():
            row.destroy()
        if not self.items:
            self.hide()
            return
        for login in self.items:
            row = tk.Frame(self.box, bg=BG)
            row.pack(fill="x")
            name = tk.Label(
                row, text=login, bg=BG, fg=INK, font=FONT, anchor="w", padx=px(10)
            )
            name.pack(side="left", fill="x", expand=True, ipady=px(3))
            name.bind("<Button-1>", lambda e, x=login: self.pick(x))
            cross = tk.Label(row, text="×", bg=BG, fg=MUTED, font=FONT, cursor="hand2")
            cross.pack(side="right", padx=px(8))
            cross.bind("<Button-1>", lambda e, x=login: self.forget(x))
        self.box.place(in_=self.entry, relx=0, rely=1, relwidth=1, y=px(2))
        self.box.lift()

    def hide(self) -> None:
        """Прячет подсказки."""
        self.box.place_forget()
        self.current = -1

    def move(self, step: int) -> str:
        """Стрелки вверх/вниз: выбирают строку подсказки."""
        if not self.box.winfo_ismapped():
            self.show()
        if not self.items:
            return "break"
        self.current = (self.current + step) % len(self.items)
        for index, row in enumerate(self.box.winfo_children()):
            color = COLORS["selected_row"] if index == self.current else BG
            row.config(bg=color)
            for child in row.winfo_children():
                child.config(bg=color)
        return "break"

    def picked(self):
        """Логин, выбранный стрелками, или None."""
        if self.box.winfo_ismapped() and 0 <= self.current < len(self.items):
            return self.items[self.current]
        return None

    def pick(self, login: str) -> None:
        """Подставляет выбранный логин и переходит к паролю."""
        self.entry.delete(0, "end")
        self.entry.insert(0, login)
        self.hide()
        self.on_pick()

    def forget(self, login: str) -> None:
        """Крестик: убирает логин из подсказок на этом компьютере."""
        try:
            settings.forget_login(login)
        except OSError:
            pass  # не удалось записать файл настроек — просто не убираем
        self.entry.focus_set()
        self.show()


class LoginFrame(ttk.Frame):
    """Окно входа по логину и паролю."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn и app.open_main).
        """
        super().__init__(app.scroll.page, padding=px((36, 24)))
        self.app = app
        ttk.Label(self, text="Вход", style="Title.TLabel").pack(pady=px((4, 12)))

        field(self, "Логин")
        self.login = ttk.Entry(self)
        self.login.pack(fill="x")
        passwords = []
        password_field(self, "Пароль", passwords)
        self.password = ttk.Entry(self, show="●")
        self.password.pack(fill="x")
        passwords.append(self.password)
        self.remember = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self, text=" Запомнить логин на этом компьютере", variable=self.remember
        ).pack(anchor="w", pady=px((8, 0)))

        self.button = ttk.Button(
            self, text="Войти", style="Accent.TButton", command=self.on_login
        )
        self.button.pack(fill="x", pady=px((14, 10)))
        self.error = Banner(self, fill="x", pady=px((12, 0)), before=self.button)

        bottom = ttk.Frame(self)
        bottom.pack()
        ttk.Label(bottom, text="Нет аккаунта?", style="Muted.TLabel").pack(side="left")
        link(bottom, "Зарегистрироваться", app.show_register).pack(side="left")

        # Подсказки логинов создаются последними, чтобы лечь поверх полей.
        self.hints = LoginHints(self.login, self.password.focus_set)
        self.login.bind("<Return>", self.on_login_enter)
        self.login.focus()
        self.password.bind("<Return>", lambda e: self.on_login())

    def on_login_enter(self, _event=None):
        """Enter в поле «Логин»: выбрать подсказку или перейти к паролю."""
        login = self.hints.picked()
        if login:
            self.hints.pick(login)
        else:
            self.hints.hide()
            self.password.focus_set()
        return "break"

    def on_login(self):
        """Проверяет логин и пароль и открывает окно по роли."""
        try:
            user = auth.login_user(self.app.conn, self.login.get(), self.password.get())
        except ValidationError as error:
            self.error.show(error.message)
            return
        try:
            if self.remember.get():
                settings.remember_login(user["login"])
            else:
                settings.forget_login(user["login"])
        except OSError:
            pass  # файл настроек недоступен — входу это не мешает
        self.app.open_main(user)


class RegisterFrame(ttk.Frame):
    """Окно регистрации с выбором роли карточками."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn, app.show_login, app.open_main).
        """
        super().__init__(app.scroll.page, padding=px((36, 20)))
        self.app = app
        ttk.Label(self, text="Регистрация", style="Title.TLabel").pack(pady=px((10, 2)))
        ttk.Label(
            self,
            text="Создайте аккаунт, чтобы вести игры или записываться на них",
            style="Muted.TLabel",
        ).pack()

        self.entries = {}
        for name in ("ФИО", "Логин"):
            field(self, name)
            self.entries[name] = ttk.Entry(self)
            self.entries[name].pack(fill="x")

        row = ttk.Frame(self)
        row.pack(fill="x")
        passwords = []  # «показать» над паролем открывает оба поля
        for column, name in enumerate(("Пароль", "Повтор")):
            box = ttk.Frame(row)
            box.grid(
                row=0, column=column, sticky="ew", padx=px((0, 8)) if column == 0 else 0
            )
            if column == 0:
                password_field(box, name, passwords)
            else:
                field(box, name)
            self.entries[name] = ttk.Entry(box, show="●")
            self.entries[name].pack(fill="x")
            passwords.append(self.entries[name])
        row.columnconfigure((0, 1), weight=1, uniform="half")

        field(self, "Роль")
        self.role = ChoiceCards(self, columns=2, wrap=150)
        self.role.set_options(ROLES)
        self.role.pack(fill="x")

        self.button = ttk.Button(
            self,
            text="Зарегистрироваться",
            style="Accent.TButton",
            command=self.on_register,
        )
        self.button.pack(fill="x", pady=px((8, 10)))
        self.error = Banner(self, fill="x", pady=px((4, 4)), before=self.button)

        bottom = ttk.Frame(self)
        bottom.pack()
        ttk.Label(bottom, text="Уже есть аккаунт?", style="Muted.TLabel").pack(
            side="left"
        )
        link(bottom, "Войти", app.show_login).pack(side="left")
        self.entries["ФИО"].focus()

    def on_register(self):
        """Регистрирует пользователя и сразу открывает окно его роли."""
        values = {name: entry.get() for name, entry in self.entries.items()}
        try:
            auth.register(
                self.app.conn,
                values["ФИО"],
                values["Логин"],
                values["Пароль"],
                values["Повтор"],
                self.role.get(),
            )
        except ValidationError as error:
            self.error.show(error.message)
            if error.field in self.entries:
                self.entries[error.field].focus()
            return
        # Как в прототипе Figma: после регистрации сразу открывается окно роли.
        user = auth.login_user(self.app.conn, values["Логин"], values["Пароль"])
        self.app.open_main(user)
