"""Окно «Профиль»: изменение ФИО и пароля, удаление аккаунта."""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.logic import auth
from gm_hub.ui.common import BG


class ProfileWindow(tk.Toplevel):
    """Отдельное окно профиля текущего пользователя."""

    def __init__(self, app):
        """Создаёт поля профиля.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(app, bg=BG, padx=20, pady=16)
        self.app = app
        self.title("Профиль")
        self.resizable(False, False)
        # Окно поверх главного; пока оно открыто, главное недоступно.
        self.transient(app)
        self.grab_set()

        user = app.user
        ttk.Label(self, text=f"Логин: {user['login']}").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(self, text=f"Роль: {auth.ROLE_NAMES[user['role']]}").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        self.entries = {}
        fields = [
            ("ФИО *", ""),
            ("Текущий пароль *", "●"),
            ("Новый пароль", "●"),
            ("Повтор нового", "●"),
        ]
        for row, (name, show) in enumerate(fields, start=2):
            ttk.Label(self, text=name).grid(row=row, column=0, sticky="w")
            entry = ttk.Entry(self, width=32, show=show)
            entry.grid(row=row, column=1, pady=4)
            self.entries[name] = entry
        self.entries["ФИО *"].insert(0, user["full_name"])
        ttk.Label(
            self, text="Новый пароль можно не заполнять.", style="Muted.TLabel"
        ).grid(row=6, column=0, columnspan=2, sticky="w")

        buttons = ttk.Frame(self)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Удалить аккаунт", command=self.on_delete).pack(
            side="left"
        )
        ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")

    def value(self, name: str) -> str:
        """Возвращает текст поля по его подписи."""
        return self.entries[name].get()

    def on_save(self):
        """Сохраняет ФИО и новый пароль."""
        user = auth.update_profile(
            self.app.conn,
            self.app.user,
            self.value("ФИО *"),
            self.value("Текущий пароль *"),
            self.value("Новый пароль"),
            self.value("Повтор нового"),
        )
        messagebox.showinfo("Профиль", "Изменения сохранены.", parent=self)
        self.destroy()
        self.app.open_main(user)  # заново открываем кабинет с новым ФИО в шапке

    def on_delete(self):
        """Удаляет аккаунт после подтверждения и возвращает к окну входа."""
        if not messagebox.askyesno(
            "Удаление аккаунта",
            "Удалить аккаунт без возможности восстановления?",
            parent=self,
        ):
            return
        auth.delete_account(
            self.app.conn, self.app.user, self.value("Текущий пароль *")
        )
        self.destroy()
        if auth.has_users(self.app.conn):
            self.app.logout()
        else:
            self.app.user = None
            self.app.show_register()
