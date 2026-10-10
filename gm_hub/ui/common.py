"""Общие элементы интерфейса по макетам Figma (п. 4.1.13 ТЗ).

Здесь карточки, кнопки-сегменты, плашки сообщений, выбор карточками,
окно кабинета со вкладками и диалоги — всё, что повторяется в нескольких
окнах. Оформление задаётся в style.py.
"""

from datetime import datetime, timedelta

from PySide6.QtCore import QDate, QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCalendarWidget,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gm_hub.config import DATETIME_FORMAT
from gm_hub.logic.errors import ValidationError
from gm_hub.settings import get_setting, write_setting
from gm_hub.ui.theme import c

# ---------------------------------------------------------------- простые


def repolish(widget) -> None:
    """Перечитывает оформление виджета после смены его свойства kind."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def label(text: str = "", kind: str | None = None, wrap: bool = False) -> QLabel:
    """Создаёт надпись.

    Args:
        text: Текст.
        kind: Вид из style.py: «muted», «small», «bold», «title» и т. д.
        wrap: Переносить ли длинный текст на новую строку.
    """
    widget = QLabel(text)
    if kind:
        widget.setProperty("kind", kind)
    widget.setWordWrap(wrap)
    return widget


def button(text: str, command=None, kind: str | None = None, small: bool = False):
    """Создаёт кнопку.

    Args:
        text: Надпись на кнопке.
        command: Функция без аргументов, вызывается по нажатию.
        kind: «accent» — зелёная главная, «danger» — с красным текстом.
        small: Компактная кнопка (в строке таблицы, в заголовке карточки).
    """
    widget = QPushButton(text)
    if kind:
        widget.setProperty("kind", kind)
    if small:
        widget.setProperty("size", "small")
    widget.setCursor(Qt.PointingHandCursor)
    if command is not None:
        widget.clicked.connect(lambda: command())
    return widget


def vbox(widget=None, margins=0, spacing=0) -> QVBoxLayout:
    """Вертикальная раскладка (виджеты друг под другом)."""
    layout = QVBoxLayout(widget) if widget is not None else QVBoxLayout()
    layout.setContentsMargins(*_margins(margins))
    layout.setSpacing(spacing)
    return layout


def hbox(widget=None, margins=0, spacing=0) -> QHBoxLayout:
    """Горизонтальная раскладка (виджеты в строку)."""
    layout = QHBoxLayout(widget) if widget is not None else QHBoxLayout()
    layout.setContentsMargins(*_margins(margins))
    layout.setSpacing(spacing)
    return layout


def _margins(value) -> tuple:
    """Отступы: число — со всех сторон, (x, y) или (слева, сверху, справа, снизу)."""
    if isinstance(value, int):
        return (value,) * 4
    if len(value) == 2:
        return (value[0], value[1], value[0], value[1])
    return tuple(value)


def clear_layout(layout) -> None:
    """Убирает из раскладки все виджеты (они сразу скрываются и удаляются)."""
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()


def hline() -> QFrame:
    """Тонкая горизонтальная линия-разделитель."""
    line = QFrame()
    line.setObjectName("line")
    line.setFixedHeight(1)
    return line


def field(layout, text: str, page: bool = False) -> QLabel:
    """Добавляет подпись над полем ввода, как в макетах.

    Args:
        layout: Раскладка, куда добавить подпись.
        text: Текст подписи.
        page: Поле лежит на зелёном фоне страницы, а не в белой карточке.
    """
    widget = label(text, "page_field" if page else "field")
    widget.setContentsMargins(0, 8, 0, 2)
    layout.addWidget(widget)
    return widget


class ClickLabel(QLabel):
    """Надпись, на которую можно нажать (ссылка «Выйти», «календарь»)."""

    clicked = Signal()

    def __init__(self, text: str = "", kind: str | None = None):
        """Создаёт надпись с курсором-рукой."""
        super().__init__(text)
        if kind:
            self.setProperty("kind", kind)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        """Щелчок левой кнопкой — сигнал clicked."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


def link(text: str, command, kind: str = "link") -> ClickLabel:
    """Создаёт текстовую ссылку («Выйти», «Зарегистрироваться»).

    Args:
        text: Текст ссылки.
        command: Функция без аргументов, вызывается по щелчку.
        kind: Вид надписи из style.py.
    """
    widget = ClickLabel(text, kind)
    widget.clicked.connect(lambda: command())
    return widget


class ClickFrame(QFrame):
    """Рамка, на которую можно нажать (карточка выбора, день календаря)."""

    clicked = Signal()

    def mousePressEvent(self, event):
        """Щелчок левой кнопкой — сигнал clicked."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ---------------------------------------------------------------- панели


class Card(QFrame):
    """Белая карточка с тонкой рамкой и скруглёнными углами, как в макетах.

    Attributes:
        body: Раскладка внутри карточки, в неё добавляются поля.
        title_label: Надпись заголовка (чтобы его менять) или None.
    """

    def __init__(self, title=None, note=None, action=None, padding=14):
        """Создаёт карточку.

        Args:
            title: Заголовок карточки.
            note: Серая подпись справа от заголовка.
            action: Кнопка справа в заголовке — пара (текст, функция).
            padding: Отступ содержимого от рамки.
        """
        super().__init__()
        self.setObjectName("card")
        outer = vbox(self)
        self.title_label = None
        if title:
            head = hbox(margins=(16, 10, 12, 10), spacing=8)
            self.title_label = label(title, "bold")
            head.addWidget(self.title_label)
            head.addStretch()
            if note:
                head.addWidget(label(note, "small"))
            if action:
                head.addWidget(button(action[0], action[1], small=True))
            outer.addLayout(head)
            outer.addWidget(hline())
        self.body = vbox(margins=padding, spacing=2)
        outer.addLayout(self.body, 1)


class Segmented(QFrame):
    """Переключатель-сегменты («Предстоящие | Прошедшие | Отменённые»)."""

    def __init__(self, options, value, on_change):
        """Создаёт кнопки-сегменты.

        Args:
            options: Список пар (подпись, значение).
            value: Значение, выбранное сначала.
            on_change: Функция без аргументов, вызывается при переключении.
        """
        super().__init__()
        self.setObjectName("seg")
        layout = hbox(self, margins=2)
        self.group = QButtonGroup(self)
        self.values = [v for _, v in options]
        self.buttons = []
        self.current = value
        for text, option in options:
            widget = button(text)
            widget.setProperty("kind", "seg")
            widget.setCheckable(True)
            widget.clicked.connect(lambda _=False, v=option: self._clicked(v))
            self.group.addButton(widget)
            self.buttons.append(widget)
            layout.addWidget(widget)
        self.on_change = on_change
        self.set_value(value)

    def value(self):
        """Возвращает выбранное значение."""
        return self.current

    def set_value(self, value) -> None:
        """Выбирает сегмент (без вызова on_change)."""
        self.current = value
        self.buttons[self.values.index(value)].setChecked(True)

    def _clicked(self, value) -> None:
        """Щелчок по сегменту."""
        self.current = value
        self.on_change()


class Banner(QFrame):
    """Цветная плашка с сообщением: ошибка (красная) или успех (зелёная).

    Пока сообщения нет, плашка скрыта и места не занимает.
    """

    def __init__(self):
        """Создаёт скрытую плашку."""
        super().__init__()
        self.setObjectName("banner")
        layout = hbox(self, margins=(14, 9, 14, 9), spacing=8)
        self.icon = QLabel()
        self.text = QLabel()
        self.text.setWordWrap(True)
        layout.addWidget(self.icon, 0, Qt.AlignTop)
        layout.addWidget(self.text, 1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(4000)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, message: str, kind: str = "error", auto_hide=True):
        """Показывает плашку.

        Зелёное сообщение об успехе само исчезает через 4 секунды, красная
        ошибка остаётся, пока её не исправят.

        Args:
            message: Текст сообщения.
            kind: «error» или «ok».
            auto_hide: Скрыть ли зелёную плашку автоматически.
        """
        self.timer.stop()
        if kind == "ok" and auto_hide:
            self.timer.start()
        if kind == "ok":
            icon, bg, fg, line = "✓", c("green_soft"), c("green_text"), c("green_line")
        else:
            icon, bg, fg, line = "!", c("red_soft"), c("red"), c("red_line")
        self.setStyleSheet(
            f"QFrame#banner {{ background: {bg}; border: 1px solid {line}; "
            f"border-radius: 8px; }} QLabel {{ color: {fg}; }}"
        )
        self.icon.setText(icon)
        self.text.setText(message)
        self.show()


class Pill(QLabel):
    """Скруглённая таблетка с текстом (статус, участник в «Составе»)."""

    def __init__(self, text: str, kind: str = "grey"):
        """Создаёт таблетку.

        Args:
            text: Текст.
            kind: «ok», «warn», «bad», «grey» или «chip» (белая с рамкой).
        """
        super().__init__(text)
        colors = {
            "ok": (c("green_soft"), c("green_text"), c("green_soft")),
            "warn": (c("yellow_soft"), c("yellow"), c("yellow_soft")),
            "bad": (c("red_soft"), c("red"), c("red_soft")),
            "grey": (c("head"), c("muted"), c("head")),
            "chip": (c("bg"), c("ink"), c("line")),
        }
        bg, fg, line = colors[kind]
        weight = 400 if kind == "chip" else 600
        self.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {line}; "
            f"border-radius: 10px; padding: 1px 9px; font-weight: {weight};"
        )
        small = self.font()
        small.setPointSize(max(small.pointSize() - 1, 8))
        self.setFont(small)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


class SeatsBar(QWidget):
    """Полоска заполненности мест: зеленеет по мере записи, полная — тёмная."""

    def __init__(self, taken: int, total: int, width: int = 70):
        """Создаёт полоску.

        Args:
            taken: Сколько мест занято (подтверждённые заявки).
            total: Лимит мест.
            width: Ширина полоски.
        """
        super().__init__()
        self.taken, self.total = taken, total
        self.setFixedSize(width, 8)
        self.setToolTip(f"Занято {taken} из {total} мест")

    def paintEvent(self, _event):
        """Рисует дорожку и закрашенную часть со скруглёнными концами."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # гладкие края
        painter.setPen(Qt.NoPen)
        w, h = self.width(), self.height()
        painter.setBrush(QColor(c("line")))
        painter.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        if self.total and self.taken:
            filled = max(w * min(self.taken, self.total) / self.total, h)
            full = self.taken >= self.total
            painter.setBrush(QColor(c("seat_taken") if full else c("green_text")))
            painter.drawRoundedRect(QRectF(0, 0, filled, h), h / 2, h / 2)


class ChoiceCards(QWidget):
    """Выбор одного варианта карточками (роль при регистрации, персонаж)."""

    def __init__(self, columns: int = 1):
        """Создаёт пустой список карточек.

        Args:
            columns: Сколько карточек в одной строке.
        """
        super().__init__()
        self.columns = columns
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        self.value = None
        self.cards = {}

    def set_options(self, options) -> None:
        """Заменяет варианты выбора.

        Args:
            options: Список троек (значение, заголовок, подпись).
        """
        clear_layout(self.grid)
        self.cards = {}
        self.value = None
        for index, (value, title, subtitle) in enumerate(options):
            box = ClickFrame()
            box.setCursor(Qt.PointingHandCursor)
            row = hbox(box, margins=(10, 7, 10, 7), spacing=8)
            mark = QLabel()
            row.addWidget(mark, 0, Qt.AlignTop)
            texts = vbox(spacing=0)
            texts.addWidget(label(title, "bold"))
            texts.addWidget(label(subtitle, "small", wrap=True))
            row.addLayout(texts, 1)
            box.clicked.connect(lambda v=value: self.select(v))
            self.grid.addWidget(box, index // self.columns, index % self.columns)
            self.cards[value] = (box, mark)
        self._paint()

    def select(self, value) -> None:
        """Выбирает вариант."""
        self.value = value
        self._paint()

    def get(self):
        """Возвращает выбранное значение или None."""
        return self.value

    def _paint(self) -> None:
        """Перекрашивает карточки: выбранная — зелёная."""
        for value, (box, mark) in self.cards.items():
            chosen = value == self.value
            bg = c("green_soft") if chosen else c("bg")
            line = c("accent") if chosen else c("line")
            box.setStyleSheet(
                f"ClickFrame {{ background: {bg}; border: 1px solid {line}; "
                "border-radius: 8px; }"
            )
            mark.setText("◉" if chosen else "○")
            mark.setStyleSheet(f"color: {c('accent') if chosen else c('muted')};")


# ---------------------------------------------------------------- тексты


class HeadingHighlighter(QSyntaxHighlighter):
    """Выделяет жирным заголовки и подписи в тексте заметки.

    Короткие строки без точки в конце — заголовки («Сцена 1. Обвал»),
    а «Внешность:» в начале строки — подпись.
    """

    def highlightBlock(self, text):
        """Проверяет одну строку текста."""
        stripped = text.strip()
        if not stripped:
            return
        bold = QTextCharFormat()
        bold.setFontWeight(QFont.DemiBold)
        if len(stripped) <= 60 and stripped[-1] not in ".,!?;:»)":
            self.setFormat(0, len(text), bold)
        elif ":" in stripped[:25]:
            self.setFormat(0, text.index(":") + 1, bold)


def make_text(height: int = 5, headings: bool = False) -> QPlainTextEdit:
    """Создаёт многострочное поле ввода.

    Args:
        height: Высота в строках (маленькое поле — ровно такой высоты,
            большое растягивается вместе с окном).
        headings: Выделять ли жирным заголовки (для заметок).
    """
    edit = QPlainTextEdit()
    edit.setTabChangesFocus(True)
    lines = edit.fontMetrics().lineSpacing() * height + 16
    if height <= 4:
        edit.setFixedHeight(lines)
    else:
        edit.setMinimumHeight(lines)
    if headings:
        edit.highlighter = HeadingHighlighter(edit.document())
    return edit


def get_text(edit: QPlainTextEdit) -> str:
    """Возвращает текст многострочного поля без пробелов по краям."""
    return edit.toPlainText().strip()


def set_text(edit: QPlainTextEdit, value: str | None) -> None:
    """Заменяет текст многострочного поля."""
    edit.setPlainText(value or "")


def password_field(layout, text: str, entries: list) -> QWidget:
    """Подпись над полем пароля со ссылкой «показать / скрыть».

    Args:
        layout: Раскладка, куда добавить подпись.
        text: Текст подписи, например «Пароль».
        entries: Список полей пароля, которые переключает ссылка (поля
            можно добавить в список уже после вызова).
    """
    row = QWidget()
    line = hbox(row, margins=(0, 8, 0, 2))
    line.addWidget(label(text, "field"))
    line.addStretch()
    switch = ClickLabel("показать", "link_muted")
    line.addWidget(switch)

    def toggle():
        hidden = entries[0].echoMode() == QLineEdit.Password
        for entry in entries:
            entry.setEchoMode(QLineEdit.Normal if hidden else QLineEdit.Password)
        switch.setText("скрыть" if hidden else "показать")

    switch.clicked.connect(toggle)
    layout.addWidget(row)
    return row


def short_name(full_name: str) -> str:
    """Сокращает ФИО для таблицы: «Жукова Полина» -> «Жукова П.»."""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    return f"{parts[0]} {parts[1][0]}."


def is_soon(db_value: str, days: int = 3) -> bool:
    """Проверяет, что сессия начнётся в ближайшие дни (запись скоро закроется).

    Args:
        db_value: Дата сессии в формате БД.
        days: Сколько дней считать «скоро».
    """
    when = datetime.strptime(db_value, DATETIME_FORMAT)
    return datetime.now() <= when <= datetime.now() + timedelta(days=days)


# ---------------------------------------------------------------- диалоги


def _message(parent, title: str, text: str, buttons):
    """Окно сообщения без значка; buttons — список пар (текст, роль)."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.NoIcon)
    made = [box.addButton(name, role) for name, role in buttons]
    box.setDefaultButton(made[0])
    box.exec()
    return made.index(box.clickedButton()) if box.clickedButton() in made else None


def info(parent, title: str, text: str) -> None:
    """Сообщение с кнопкой «OK»."""
    _message(parent, title, text, [("OK", QMessageBox.AcceptRole)])


def ask(parent, title: str, text: str) -> bool:
    """Вопрос «Да / Нет».

    Returns:
        True, если нажато «Да».
    """
    answer = _message(
        parent, title, text, [("Да", QMessageBox.YesRole), ("Нет", QMessageBox.NoRole)]
    )
    return answer == 0


def ask_save(parent):
    """Вопрос о несохранённых изменениях.

    Returns:
        True — сохранить, False — не сохранять, None — отмена.
    """
    answer = _message(
        parent,
        "Несохранённые изменения",
        "Сохранить изменения?",
        [
            ("Сохранить", QMessageBox.AcceptRole),
            ("Не сохранять", QMessageBox.DestructiveRole),
            ("Отмена", QMessageBox.RejectRole),
        ],
    )
    return {0: True, 1: False}.get(answer)


def ask_text(parent, title: str, prompt: str):
    """Небольшое окно с одним полем ввода (например, причина отказа).

    Returns:
        Введённый текст (может быть пустым) или None, если нажата «Отмена».
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = vbox(dialog, margins=(20, 14, 20, 16), spacing=2)
    field(layout, prompt)
    entry = QLineEdit()
    entry.setMinimumWidth(360)
    layout.addWidget(entry)
    layout.addSpacing(14)
    row = hbox(spacing=6)
    row.addStretch()
    row.addWidget(button("Отмена", dialog.reject))
    ok = button("Отклонить", dialog.accept, "accent")
    ok.setDefault(True)
    row.addWidget(ok)
    layout.addLayout(row)
    entry.returnPressed.connect(dialog.accept)
    if dialog.exec() == QDialog.Accepted:
        return entry.text()
    return None


class DatePicker(QDialog):
    """Небольшой календарь: щелчок по дню подставляет дату в поле «Дата»."""

    def __init__(self, entry):
        """Открывает календарь под полем.

        Args:
            entry: Поле даты «ДД.ММ.ГГГГ»; месяц берётся из уже введённой даты.
        """
        super().__init__(entry, Qt.Popup)
        self.entry = entry
        layout = vbox(self, margins=6)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setMinimumDate(QDate.currentDate())  # прошедшие дни нельзя
        shown = QDate.fromString(entry.text(), "dd.MM.yyyy")
        if shown.isValid():
            self.calendar.setSelectedDate(shown)
        self.calendar.clicked.connect(self.pick)
        layout.addWidget(self.calendar)
        self.move(entry.mapToGlobal(QPoint(0, entry.height() + 4)))
        entry.picker = self  # окно живёт, пока открыто
        self.show()

    def pick(self, day: QDate) -> None:
        """Подставляет выбранную дату в поле и закрывает календарь."""
        self.entry.setText(day.toString("dd.MM.yyyy"))
        self.entry.setFocus()
        self.close()


# ---------------------------------------------------------------- кабинет


class FormGuard:
    """Добавка к вкладке с формой: не даёт потерять несохранённые правки.

    Вкладка задаёт form_state() — текущие значения полей, on_save() и
    discard() — вернуть сохранённые значения. После загрузки и сохранения
    формы вкладка вызывает remember().
    """

    def remember(self) -> None:
        """Запоминает значения полей как сохранённые."""
        self.saved_state = self.form_state()

    def is_dirty(self) -> bool:
        """Есть ли в форме несохранённые изменения."""
        return self.form_state() != getattr(self, "saved_state", None)

    def can_leave(self) -> bool:
        """Спрашивает, сохранить ли изменения, перед уходом с формы.

        Returns:
            True — можно уходить (сохранено или правки отброшены),
            False — пользователь нажал «Отмена» или сохранить не удалось.
        """
        if not self.is_dirty():
            return True
        answer = ask_save(self)
        if answer is None:
            return False
        if answer:
            try:
                self.on_save()
            except ValidationError as error:
                info(self, "Проверьте данные", error.message)
                return False
            return not self.is_dirty()
        self.discard()
        return True


class Tab(QFrame):
    """Общая основа вкладки: мятный фон и доступ к БД и пользователю.

    Attributes:
        main: Окно кабинета (шапка, вкладки, строка итогов).
        app: Приложение (app.conn, app.user).
        box: Раскладка вкладки.
    """

    def __init__(self, main, app, direction: str = "v"):
        """Создаёт вкладку.

        Args:
            main: Окно кабинета.
            app: Приложение.
            direction: «v» — содержимое сверху вниз, «h» — слева направо.
        """
        super().__init__()
        self.setObjectName("page")
        self.main = main
        self.app = app
        make = vbox if direction == "v" else hbox
        self.box = make(self, margins=16, spacing=12)

    def status(self, text: str) -> None:
        """Пишет итоги вкладки в строку внизу окна."""
        self.main.set_status(text)

    def can_leave(self) -> bool:
        """На вкладке без формы уходить можно всегда."""
        return True


class MainFrame(QFrame):
    """Окно кабинета, как в образцах: шапка, вкладки, строка итогов внизу."""

    def __init__(self, app, subtitle: str, tabs):
        """Создаёт шапку, вкладки и строку итогов.

        Args:
            app: Приложение (app.user, app.logout, app.show_profile).
            subtitle: Подпись под названием программы.
            tabs: Список пар (название вкладки, класс вкладки).
        """
        super().__init__()
        self.setObjectName("page")
        self.app = app
        layout = vbox(self)

        header = QFrame()
        header.setObjectName("header")
        head = hbox(header, margins=(16, 10, 16, 0))
        brand = vbox(spacing=0)
        brand.setContentsMargins(0, 0, 0, 10)
        brand.addWidget(label("Game Master Hub", "logo"))
        brand.addWidget(label(subtitle, "head_small"))
        head.addLayout(brand)
        head.addSpacing(28)
        bar = QWidget()
        tabs_row = hbox(bar, spacing=2)
        head.addWidget(bar, 0, Qt.AlignBottom)
        head.addStretch()
        user = vbox(spacing=2)
        user.setContentsMargins(16, 0, 0, 10)
        name = label(app.user["full_name"], "head_bold")
        name.setAlignment(Qt.AlignRight)
        user.addWidget(name)
        links = hbox(spacing=14)
        links.addStretch()
        theme_text = "Светлая тема" if app.is_dark() else "Тёмная тема"
        for text, command in (
            ("Справка", app.show_help),
            (theme_text, app.toggle_theme),
            ("Профиль", app.show_profile),
            ("Выйти", app.logout),
        ):
            links.addWidget(link(text, command, "head_link"))
        user.addLayout(links)
        head.addLayout(user)
        layout.addWidget(header)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        footer = QFrame()
        footer.setObjectName("footer")
        self.status = label("", "small")
        hbox(footer, margins=(16, 6)).addWidget(self.status)
        layout.addWidget(footer)

        self.tab_titles = [title for title, _ in tabs]
        self.tab_buttons = []
        self.tabs = []
        self.shown = None  # номер вкладки, которая сейчас на экране
        group = QButtonGroup(self)
        for index, (title, tab_class) in enumerate(tabs):
            tab_button = button(title)
            tab_button.setProperty("kind", "tab")
            tab_button.setCheckable(True)
            tab_button.clicked.connect(lambda _=False, i=index: self.show_tab(i))
            group.addButton(tab_button)
            tabs_row.addWidget(tab_button)
            self.tab_buttons.append(tab_button)
            tab = tab_class(self, app)
            self.stack.addWidget(tab)
            self.tabs.append(tab)

        # Горячие клавиши: Ctrl+S, Ctrl+N, Ctrl+F, Delete и F1 (справка).
        for keys, action in (
            ("Ctrl+S", self.on_save_key),
            ("Ctrl+N", self.on_new_key),
            ("Ctrl+F", self.on_find_key),
            ("Delete", self.on_delete_key),
            ("F1", app.show_help),
        ):
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(action)

        # Открывается вкладка, на которой пользователь был в прошлый раз.
        self.tab_key = "tab_" + app.user["role"]
        saved = get_setting(self.tab_key, 0)
        self.show_tab(saved if isinstance(saved, int) and saved < len(tabs) else 0)
        # Раз в 30 секунд обновляются числа на вкладках (новые заявки, решения).
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_badges)
        self.timer.start(30000)

    def update_badges(self) -> None:
        """Обновляет числа на вкладках; переопределяется в окнах."""

    def current_tab(self):
        """Открытая сейчас вкладка."""
        return self.tabs[self.shown]

    def on_save_key(self) -> None:
        """Ctrl+S — сохранить форму на открытой вкладке."""
        if hasattr(self.current_tab(), "on_save"):
            self.current_tab().on_save()

    def on_new_key(self) -> None:
        """Ctrl+N — новая запись на открытой вкладке."""
        if hasattr(self.current_tab(), "on_new"):
            self.current_tab().on_new()

    def on_find_key(self) -> None:
        """Ctrl+F — перейти к полю поиска."""
        search = getattr(self.current_tab(), "search", None)
        if search is not None:
            search.setFocus()
            search.selectAll()

    def on_delete_key(self) -> None:
        """Delete удаляет выбранную строку (в полях ввода — обычное удаление)."""
        tab = self.current_tab()
        action = getattr(tab, "on_delete", None) or getattr(tab, "on_withdraw", None)
        if action:
            action()

    def show_tab(self, index: int) -> None:
        """Показывает вкладку и перечитывает её данные из БД.

        Если на открытой вкладке есть несохранённые изменения, сначала
        спрашивает, сохранить ли их; при «Отмене» вкладка не меняется.

        Args:
            index: Номер вкладки.
        """
        if self.shown is not None and index != self.shown:
            if not self.tabs[self.shown].can_leave():
                self.tab_buttons[self.shown].setChecked(True)
                return
        self.shown = index
        self.tab_buttons[index].setChecked(True)
        try:
            write_setting(self.tab_key, index)
        except OSError:
            pass  # файл настроек недоступен — просто не запоминаем вкладку
        self.stack.setCurrentIndex(index)
        self.set_status("")
        self.tabs[index].refresh()
        self.update_badges()

    def can_leave(self) -> bool:
        """Проверяет несохранённые изменения на открытой вкладке."""
        return self.shown is None or self.tabs[self.shown].can_leave()

    def set_badge(self, index: int, count: int) -> None:
        """Показывает число рядом с названием вкладки: «Мои записи (2)»."""
        title = self.tab_titles[index]
        self.tab_buttons[index].setText(f"{title} ({count})" if count else title)

    def set_status(self, text: str) -> None:
        """Пишет текст в строку итогов внизу окна."""
        self.status.setText(text)
