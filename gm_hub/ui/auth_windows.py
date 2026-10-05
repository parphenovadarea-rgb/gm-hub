"""Окна «Вход» и «Регистрация» (макеты 01 и 02)."""

from tkinter import ttk

from gm_hub.logic import auth
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import Banner, ChoiceCards, field, link

ROLES = [
    ("GM", "Мастер", "создаю сессии, веду сюжет"),
    ("PLAYER", "Игрок", "веду персонажей, записываюсь"),
]


class LoginFrame(ttk.Frame):
    """Окно входа по логину и паролю."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn и app.open_main).
        """
        super().__init__(app, padding=(40, 30))
        self.app = app
        ttk.Label(self, text="Вход", style="Title.TLabel").pack(pady=(30, 16))

        field(self, "Логин")
        self.login = ttk.Entry(self)
        self.login.pack(fill="x")
        field(self, "Пароль")
        self.password = ttk.Entry(self, show="●")
        self.password.pack(fill="x")

        self.button = ttk.Button(
            self, text="Войти", style="Accent.TButton", command=self.on_login
        )
        self.button.pack(fill="x", pady=(16, 10))
        self.error = Banner(self, fill="x", pady=(12, 0), before=self.button)

        bottom = ttk.Frame(self)
        bottom.pack()
        ttk.Label(bottom, text="Нет аккаунта?", style="Muted.TLabel").pack(side="left")
        link(bottom, "Зарегистрироваться", app.show_register).pack(side="left")

        self.login.focus()
        self.password.bind("<Return>", lambda e: self.on_login())

    def on_login(self):
        """Проверяет логин и пароль и открывает окно по роли."""
        try:
            user = auth.login_user(self.app.conn, self.login.get(), self.password.get())
        except ValidationError as error:
            self.error.show(error.message)
            return
        self.app.open_main(user)


class RegisterFrame(ttk.Frame):
    """Окно регистрации с выбором роли карточками."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn, app.show_login, app.open_main).
        """
        super().__init__(app, padding=(40, 20))
        self.app = app
        ttk.Label(self, text="Регистрация", style="Title.TLabel").pack(pady=(10, 2))
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
        for column, name in enumerate(("Пароль", "Повтор")):
            box = ttk.Frame(row)
            box.grid(
                row=0, column=column, sticky="ew", padx=(0, 8) if column == 0 else 0
            )
            field(box, name)
            self.entries[name] = ttk.Entry(box, show="●")
            self.entries[name].pack(fill="x")
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
        self.button.pack(fill="x", pady=(8, 10))
        self.error = Banner(self, fill="x", pady=(4, 4), before=self.button)

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
