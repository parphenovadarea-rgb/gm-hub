"""Окно «Профиль»: изменение ФИО и пароля, удаление аккаунта."""

from PySide6.QtWidgets import QCheckBox, QDialog, QGridLayout, QLineEdit, QWidget

from gm_hub.logic import auth
from gm_hub.ui import style
from gm_hub.ui.common import ask, button, field, hbox, info, label, vbox


class ProfileWindow(QDialog):
    """Отдельное окно профиля текущего пользователя."""

    def __init__(self, app):
        """Создаёт поля профиля.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Профиль")
        layout = vbox(self, margins=(22, 16, 22, 18), spacing=2)

        user = app.user
        layout.addWidget(label("Профиль", "title"))
        layout.addWidget(
            label(
                f"Логин: {user['login']}  ·  {auth.ROLE_NAMES[user['role']]}", "muted"
            )
        )
        self.entries = {}
        for name, hidden in (("ФИО *", False), ("Текущий пароль *", True)):
            field(layout, name)
            self.entries[name] = QLineEdit()
            if hidden:
                self.entries[name].setEchoMode(QLineEdit.Password)
            layout.addWidget(self.entries[name])
        row = QGridLayout()
        row.setHorizontalSpacing(8)
        for column, name in enumerate(("Новый пароль", "Повтор нового")):
            box = QWidget()
            inner = vbox(box, spacing=2)
            field(inner, name)
            self.entries[name] = QLineEdit()
            self.entries[name].setEchoMode(QLineEdit.Password)
            inner.addWidget(self.entries[name])
            row.addWidget(box, 0, column)
        layout.addLayout(row)
        self.entries["ФИО *"].setText(user["full_name"])
        self.entries["ФИО *"].setMinimumWidth(380)
        layout.addSpacing(4)
        layout.addWidget(label("Новый пароль можно не заполнять.", "small"))
        layout.addSpacing(10)
        # Настройка вида для этого компьютера: окно перерисовывается сразу.
        self.large_text = QCheckBox("Крупный текст (шрифт больше на 15 %)")
        self.large_text.setChecked(style.LARGE_TEXT)
        self.large_text.toggled.connect(self.on_large_text)
        layout.addWidget(self.large_text)
        layout.addSpacing(14)

        buttons = hbox(spacing=6)
        buttons.addWidget(button("Удалить аккаунт", self.on_delete, "danger"))
        buttons.addStretch()
        buttons.addWidget(button("Сохранить", self.on_save, "accent"))
        layout.addLayout(buttons)

    def on_large_text(self, on: bool):
        """Включает или выключает крупный текст и перерисовывает окно."""
        self.close()
        self.app.set_large_text(on)

    def value(self, name: str) -> str:
        """Возвращает текст поля по его подписи."""
        return self.entries[name].text()

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
        info(self, "Профиль", "Изменения сохранены.")
        self.close()
        self.app.open_main(user)  # заново открываем кабинет с новым ФИО в шапке

    def on_delete(self):
        """Удаляет аккаунт после подтверждения и возвращает к окну входа."""
        if not ask(
            self, "Удаление аккаунта", "Удалить аккаунт без возможности восстановления?"
        ):
            return
        auth.delete_account(
            self.app.conn, self.app.user, self.value("Текущий пароль *")
        )
        self.close()
        if auth.has_users(self.app.conn):
            self.app.logout()
        else:
            self.app.user = None
            self.app.show_register()
