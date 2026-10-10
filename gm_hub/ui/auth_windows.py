"""Окна «Вход» и «Регистрация» (макеты 01 и 02)."""

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QFrame, QGridLayout, QLineEdit, QWidget

from gm_hub import settings
from gm_hub.logic import auth
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    Banner,
    ChoiceCards,
    ClickLabel,
    button,
    clear_layout,
    field,
    hbox,
    label,
    link,
    password_field,
    vbox,
)
from gm_hub.ui.theme import c

ROLES = [
    ("GM", "Мастер", "создаю сессии, веду сюжет"),
    ("PLAYER", "Игрок", "веду персонажей, записываюсь"),
]


class LoginHints(QObject):
    """Подсказки логинов под полем «Логин», как в браузере.

    Показывает логины, с которыми уже входили на этом компьютере. Выбрать —
    щелчком или стрелками и Enter; крестик убирает логин из подсказок.
    """

    def __init__(self, entry, owner, on_pick):
        """Создаёт выпадающий список (пока скрытый).

        Args:
            entry: Поле «Логин».
            owner: Карточка окна входа — список лежит поверх её полей.
            on_pick: Что сделать после выбора логина (перейти к паролю).
        """
        super().__init__(owner)
        self.entry = entry
        self.owner = owner
        self.on_pick = on_pick
        self.items = []  # подсказанные логины
        self.current = -1  # выбранная стрелками строка
        self.box = QFrame(owner)
        self.box.setObjectName("hints")
        self.box.setStyleSheet(
            f"QFrame#hints {{ background: {c('bg')}; border: 1px solid "
            f"{c('line')}; border-radius: 6px; }}"
        )
        self.rows = vbox(self.box, margins=1)
        self.box.hide()
        entry.textEdited.connect(lambda _text: self.show())
        entry.installEventFilter(self)

    def eventFilter(self, _obj, event):
        """Стрелки, Esc, щелчок и уход из поля «Логин»."""
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down:
                self.move(1)
                return True
            if event.key() == Qt.Key_Up:
                self.move(-1)
                return True
            if event.key() == Qt.Key_Escape and self.box.isVisible():
                self.hide()
                return True
        elif event.type() == QEvent.MouseButtonPress:
            QTimer.singleShot(0, self.show)
        elif event.type() == QEvent.FocusOut:
            self.hide()
        return False

    def show(self) -> None:
        """Показывает логины, подходящие под введённый текст."""
        self.items = settings.matching_logins(self.entry.text())
        self.current = -1
        clear_layout(self.rows)
        if not self.items:
            self.hide()
            return
        for login in self.items:
            row = QFrame()
            line = hbox(row, margins=(10, 4, 8, 4))
            name = ClickLabel(login)
            name.clicked.connect(lambda x=login: self.pick(x))
            line.addWidget(name, 1)
            cross = ClickLabel("×", "muted")
            cross.setToolTip("Убрать логин из подсказок")
            cross.clicked.connect(lambda x=login: self.forget(x))
            line.addWidget(cross)
            self.rows.addWidget(row)
        place = self.entry.mapTo(self.owner, QPoint(0, self.entry.height() + 2))
        self.box.setGeometry(
            place.x(), place.y(), self.entry.width(), self.box.sizeHint().height()
        )
        self.box.raise_()
        self.box.show()

    def hide(self) -> None:
        """Прячет подсказки."""
        self.box.hide()
        self.current = -1

    def move(self, step: int) -> None:
        """Стрелки вверх/вниз: выбирают строку подсказки."""
        if not self.box.isVisible():
            self.show()
        if not self.items:
            return
        self.current = (self.current + step) % len(self.items)
        for index in range(self.rows.count()):
            row = self.rows.itemAt(index).widget()
            color = c("selected_row") if index == self.current else "transparent"
            row.setStyleSheet(f"background: {color}; border-radius: 4px;")

    def picked(self):
        """Логин, выбранный стрелками, или None."""
        if self.box.isVisible() and 0 <= self.current < len(self.items):
            return self.items[self.current]
        return None

    def pick(self, login: str) -> None:
        """Подставляет выбранный логин и переходит к паролю."""
        self.entry.setText(login)
        self.hide()
        self.on_pick()

    def forget(self, login: str) -> None:
        """Крестик: убирает логин из подсказок на этом компьютере."""
        try:
            settings.forget_login(login)
        except OSError:
            pass  # не удалось записать файл настроек — просто не убираем
        self.entry.setFocus()
        self.show()


class LoginFrame(QFrame):
    """Окно входа по логину и паролю."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn и app.open_main).
        """
        super().__init__()
        self.setObjectName("card")
        self.app = app
        layout = vbox(self, margins=(36, 24, 36, 24), spacing=2)
        title = label("Вход", "title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(8)

        field(layout, "Логин")
        self.login = QLineEdit()
        layout.addWidget(self.login)
        passwords = []
        password_field(layout, "Пароль", passwords)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)
        passwords.append(self.password)
        layout.addSpacing(8)
        self.remember = QCheckBox("Запомнить логин на этом компьютере")
        self.remember.setChecked(True)
        layout.addWidget(self.remember)
        layout.addSpacing(12)
        self.error = Banner()
        layout.addWidget(self.error)
        layout.addSpacing(4)
        layout.addWidget(button("Войти", self.on_login, "accent"))
        layout.addSpacing(10)

        bottom = hbox(spacing=4)
        bottom.addStretch()
        bottom.addWidget(label("Нет аккаунта?", "muted"))
        bottom.addWidget(link("Зарегистрироваться", app.show_register))
        bottom.addStretch()
        layout.addLayout(bottom)

        self.hints = LoginHints(self.login, self, self.password.setFocus)
        self.login.returnPressed.connect(self.on_login_enter)
        self.password.returnPressed.connect(self.on_login)
        self.login.setFocus()

    def on_login_enter(self):
        """Enter в поле «Логин»: выбрать подсказку или перейти к паролю."""
        login = self.hints.picked()
        if login:
            self.hints.pick(login)
        else:
            self.hints.hide()
            self.password.setFocus()

    def on_login(self):
        """Проверяет логин и пароль и открывает окно по роли."""
        try:
            user = auth.login_user(
                self.app.conn, self.login.text(), self.password.text()
            )
        except ValidationError as error:
            self.error.show_message(error.message)
            return
        try:
            if self.remember.isChecked():
                settings.remember_login(user["login"])
            else:
                settings.forget_login(user["login"])
        except OSError:
            pass  # файл настроек недоступен — входу это не мешает
        self.app.open_main(user)


class RegisterFrame(QFrame):
    """Окно регистрации с выбором роли карточками."""

    def __init__(self, app):
        """Создаёт поля и кнопки окна.

        Args:
            app: Приложение (нужны app.conn, app.show_login, app.open_main).
        """
        super().__init__()
        self.setObjectName("card")
        self.app = app
        layout = vbox(self, margins=(36, 20, 36, 22), spacing=2)
        title = label("Регистрация", "title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        hint = label(
            "Создайте аккаунт, чтобы вести игры или записываться на них", "muted"
        )
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self.entries = {}
        for name in ("ФИО", "Логин"):
            field(layout, name)
            self.entries[name] = QLineEdit()
            layout.addWidget(self.entries[name])

        passwords = []  # «показать» над паролем открывает оба поля
        row = QGridLayout()
        row.setHorizontalSpacing(8)
        row.setVerticalSpacing(0)
        for column, name in enumerate(("Пароль", "Повтор")):
            box = QWidget()
            inner = vbox(box, spacing=2)
            if column == 0:
                password_field(inner, name, passwords)
            else:
                field(inner, name)
            entry = QLineEdit()
            entry.setEchoMode(QLineEdit.Password)
            inner.addWidget(entry)
            self.entries[name] = entry
            passwords.append(entry)
            row.addWidget(box, 0, column)
        layout.addLayout(row)

        field(layout, "Роль")
        self.role = ChoiceCards(columns=2)
        self.role.set_options(ROLES)
        layout.addWidget(self.role)
        layout.addSpacing(10)
        self.error = Banner()
        layout.addWidget(self.error)
        layout.addSpacing(4)
        layout.addWidget(button("Зарегистрироваться", self.on_register, "accent"))
        layout.addSpacing(10)

        bottom = hbox(spacing=4)
        bottom.addStretch()
        bottom.addWidget(label("Уже есть аккаунт?", "muted"))
        bottom.addWidget(link("Войти", app.show_login))
        bottom.addStretch()
        layout.addLayout(bottom)
        for entry in self.entries.values():
            entry.returnPressed.connect(self.on_register)
        self.entries["ФИО"].setFocus()

    def on_register(self):
        """Регистрирует пользователя и сразу открывает окно его роли."""
        values = {name: entry.text() for name, entry in self.entries.items()}
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
            self.error.show_message(error.message)
            if error.field in self.entries:
                self.entries[error.field].setFocus()
            return
        # Как в прототипе Figma: после регистрации сразу открывается окно роли.
        user = auth.login_user(self.app.conn, values["Логин"], values["Пароль"])
        self.app.open_main(user)
