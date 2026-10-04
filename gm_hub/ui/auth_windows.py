"""Окна «Вход» и «Регистрация» (макеты 01 и 02)."""

import tkinter as tk
from tkinter import ttk

from gm_hub.logic import auth
from gm_hub.logic.errors import ValidationError


class LoginFrame(ttk.Frame):
    """Окно входа по логину и паролю."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn и app.open_main).
        """
        super().__init__(app, padding=30)
        self.app = app
        card = ttk.Frame(self)
        card.place(relx=0.5, rely=0.45, anchor="center")

        ttk.Label(card, text="Game Master Hub", style="Title.TLabel").pack()
        ttk.Label(
            card, text="Ассистент ведущего настольных ролевых игр", style="Muted.TLabel"
        ).pack(pady=(0, 20))

        ttk.Label(card, text="Логин").pack(anchor="w")
        self.login = ttk.Entry(card, width=36)
        self.login.pack(pady=(0, 10))
        ttk.Label(card, text="Пароль").pack(anchor="w")
        self.password = ttk.Entry(card, width=36, show="●")
        self.password.pack(pady=(0, 10))

        self.error = ttk.Label(card, style="Error.TLabel")
        self.error.pack()
        ttk.Button(
            card, text="Войти", style="Accent.TButton", command=self.on_login
        ).pack(fill="x", pady=10)
        ttk.Label(card, text="Нет аккаунта?", style="Muted.TLabel").pack()
        ttk.Button(card, text="Зарегистрироваться", command=app.show_register).pack()

        self.login.focus()
        self.password.bind("<Return>", lambda e: self.on_login())

    def on_login(self):
        """Проверяет логин и пароль и открывает окно по роли."""
        try:
            user = auth.login_user(self.app.conn, self.login.get(), self.password.get())
        except ValidationError as error:
            self.error.config(text=error.message)
            return
        self.app.open_main(user)


class RegisterFrame(ttk.Frame):
    """Окно регистрации с выбором роли."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn, app.show_login).
        """
        super().__init__(app, padding=30)
        self.app = app
        card = ttk.Frame(self)
        card.place(relx=0.5, rely=0.45, anchor="center")

        ttk.Label(card, text="Регистрация", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2
        )
        ttk.Label(
            card,
            text="Создайте аккаунт, чтобы вести игры или записываться на них",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 16))

        self.entries = {}
        fields = [("ФИО", ""), ("Логин", ""), ("Пароль", "●"), ("Повтор", "●")]
        for row, (name, show) in enumerate(fields, start=2):
            ttk.Label(card, text=name + " *").grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(card, width=34, show=show)
            entry.grid(row=row, column=1, pady=4)
            self.entries[name] = entry

        ttk.Label(card, text="Роль *").grid(row=6, column=0, sticky="nw", pady=6)
        self.role = tk.StringVar(value="PLAYER")
        roles = ttk.Frame(card)
        roles.grid(row=6, column=1, sticky="w", pady=6)
        ttk.Radiobutton(
            roles,
            text="Мастер — создаю сессии, веду сюжет",
            value="GM",
            variable=self.role,
        ).pack(anchor="w")
        ttk.Radiobutton(
            roles,
            text="Игрок — веду персонажей, записываюсь",
            value="PLAYER",
            variable=self.role,
        ).pack(anchor="w")

        self.error = ttk.Label(card, style="Error.TLabel")
        self.error.grid(row=7, column=0, columnspan=2)
        ttk.Button(
            card,
            text="Зарегистрироваться",
            style="Accent.TButton",
            command=self.on_register,
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Button(card, text="Уже есть аккаунт? Войти", command=app.show_login).grid(
            row=9, column=0, columnspan=2
        )
        self.entries["ФИО"].focus()

    def on_register(self):
        """Регистрирует пользователя и переходит к окну входа."""
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
            self.error.config(text=error.message)
            self.entries.get(error.field, self.entries["ФИО"]).focus()
            return
        # Как в прототипе Figma: после регистрации сразу открывается окно роли.
        user = auth.login_user(self.app.conn, values["Логин"], values["Пароль"])
        self.app.open_main(user)
