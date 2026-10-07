"""Окно «Профиль»: изменение ФИО и пароля, удаление аккаунта."""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.logic import auth
from gm_hub.ui.common import BG, field, px


class ProfileWindow(tk.Toplevel):
    """Отдельное окно профиля текущего пользователя."""

    def __init__(self, app):
        """Создаёт поля профиля.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(app, bg=BG, padx=px(20), pady=px(16))
        self.app = app
        self.title("Профиль")
        self.resizable(False, False)
        # Окно поверх главного; пока оно открыто, главное недоступно.
        self.transient(app)
        self.grab_set()

        user = app.user
        ttk.Label(self, text="Профиль", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self,
            text=f"Логин: {user['login']}  ·  {auth.ROLE_NAMES[user['role']]}",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=px((0, 4)))

        self.entries = {}
        for name, show in (("ФИО *", ""), ("Текущий пароль *", "●")):
            field(self, name)
            self.entries[name] = ttk.Entry(self, width=36, show=show)
            self.entries[name].pack(fill="x")
        row = ttk.Frame(self)
        row.pack(fill="x")
        for column, name in enumerate(("Новый пароль", "Повтор нового")):
            box = ttk.Frame(row)
            box.grid(
                row=0, column=column, sticky="ew", padx=px((0, 8)) if column == 0 else 0
            )
            field(box, name)
            self.entries[name] = ttk.Entry(box, show="●")
            self.entries[name].pack(fill="x")
        row.columnconfigure((0, 1), weight=1, uniform="half")
        self.entries["ФИО *"].insert(0, user["full_name"])
        ttk.Label(
            self, text="Новый пароль можно не заполнять.", style="Small.TLabel"
        ).pack(anchor="w", pady=px((4, 0)))

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=px((14, 0)))
        ttk.Button(
            buttons,
            text="Удалить аккаунт",
            style="Danger.TButton",
            command=self.on_delete,
        ).pack(side="left")
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
