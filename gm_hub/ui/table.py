"""Таблицы и списки в стиле макетов Figma.

Таблица — это QTableWidget, а в каждую ячейку кладётся небольшой виджет:
так в ячейке может быть жирное название с серой подписью, цветной статус-
«таблетка», полоска мест или кнопки. Выбранная строка подсвечивается,
по заголовку столбца — сортировка.

Ячейка описывается простым значением:
    "текст"                          — обычный текст;
    ("bold", "текст")                — жирный;
    ("muted", "текст")               — серый;
    ("small", "ТЕКСТ")               — мелкий серый (подпись категории);
    ("pill", "Подтверждена", "ok")   — таблетка: ok, warn, bad, grey, chip;
    ("seats", занято, свободно)      — полоска заполненности мест;
    ("line", [часть, часть, ...])    — части в одну строку;
    ("stack", [часть, часть, ...])   — части друг под другом;
    ("buttons", [(текст, вид, функция, активна[, подсказка]), ...]) — кнопки.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from gm_hub.ui.common import Pill, SeatsBar, button, hbox, label, vbox
from gm_hub.ui.theme import c

# Статусы из БД -> вид таблетки
STATUS_PILL = {
    "PENDING": "warn",
    "CONFIRMED": "ok",
    "REJECTED": "bad",
    "PLANNED": "ok",
    "CLOSED": "grey",
    "CANCELLED": "bad",
}


def hint_for(text: str):
    """Подсказка при наведении для метки в таблице (или None).

    Args:
        text: Текст метки, например «СКОРО» или «№1 в очереди».
    """
    hints = {
        "СКОРО": "До начала меньше 3 дней — скоро запись закроется",
        "новое": "Решение Мастера принято после вашего прошлого просмотра",
        "На рассмотрении": "Мастер ещё не принял решение по заявке",
    }
    if text in hints:
        return hints[text]
    if "в очереди" in text:
        return (
            "Мест нет: заявка в листе ожидания. Её подтвердят, когда место "
            "освободится"
        )
    return None


class RowTable(QTableWidget):
    """Таблица или список строк в стиле макетов.

    Attributes:
        selected: id выбранной строки или None.
        rows: id строки -> словарь с ячейками, цветом и значениями сортировки.
    """

    def __init__(
        self, columns, header=True, on_select=None, on_double=None, flat=False
    ):
        """Создаёт пустую таблицу.

        Args:
            columns: Список (заголовок, ширина, растягивать ли столбец).
            header: Показывать ли строку заголовков.
            on_select: Функция, вызываемая с id строки при её выборе.
            on_double: Функция, вызываемая с id строки при двойном щелчке.
            flat: Без рамки (таблица уже лежит внутри карточки).
        """
        super().__init__(0, len(columns))
        self.columns = columns
        self.on_select = on_select
        self.on_double = on_double
        self.selected = None
        self.rows = {}
        self.order = []  # id строк в том порядке, как они показаны
        self.sort_column = None
        self.sort_reverse = False
        self.hovered = None  # номер строки под курсором
        self.quiet = False  # True — выбор строки из кода, on_select не зовём
        if flat:
            self.setProperty("flat", True)

        self.setHorizontalHeaderLabels([title for title, _, _ in columns])
        head = self.horizontalHeader()
        for index, (_, width, stretch) in enumerate(columns):
            mode = QHeaderView.Stretch if stretch else QHeaderView.Fixed
            head.setSectionResizeMode(index, mode)
            self.setColumnWidth(index, width)
        self.setMinimumWidth(sum(width for _, width, _ in columns) + 4)
        head.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        head.setHighlightSections(False)
        head.setSectionsClickable(header)
        head.sectionClicked.connect(self.sort_by)
        head.setVisible(header)
        head.sectionResized.connect(self.fit_later)
        self.verticalHeader().hide()
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.cellEntered.connect(self._hover)
        self.itemSelectionChanged.connect(self._selection_changed)
        self.cellDoubleClicked.connect(self._double)

        # Подсказка в пустой таблице: что сделать, чтобы здесь появились данные.
        self.empty = label("", "muted")
        self.empty.setParent(self.viewport())
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.hide()
        # Высота строк считается, когда Qt разложит ячейки (через таймер).
        self.fit_timer = QTimer(self)
        self.fit_timer.setSingleShot(True)
        self.fit_timer.timeout.connect(self.fit_rows)

    # ------------------------------------------------------------ строки

    def clear(self, empty_text: str = "") -> None:
        """Удаляет все строки.

        Args:
            empty_text: Подпись, которая показывается, пока строк нет.
        """
        self.quiet = True
        self.setRowCount(0)
        self.quiet = False
        self.rows = {}
        self.order = []
        self.selected = None
        self.hovered = None
        self.empty.setText(empty_text)
        self.empty.setVisible(bool(empty_text))
        self._place_empty()

    def add(self, row_id, cells, sort=None, highlight=False) -> None:
        """Добавляет строку в конец таблицы.

        Args:
            row_id: id записи в БД — по нему строку потом выбирают.
            cells: Ячейки по числу столбцов (формат — в описании модуля).
            sort: Значения для сортировки по столбцам (по умолчанию — текст).
            highlight: Подсветка строки: True — жёлтая (новая заявка),
                "soon" — зелёная (сессия скоро).
        """
        self.empty.hide()
        bg = {True: c("pending_row"), "soon": c("soon_row")}.get(highlight)
        values = sort if sort is not None else [_cell_text(cell) for cell in cells]
        self.rows[row_id] = {"cells": cells, "bg": bg, "values": values}
        self.order.append(row_id)
        self._insert(row_id)

    def _insert(self, row_id) -> None:
        """Рисует строку в конце таблицы."""
        row = self.rows[row_id]
        number = self.rowCount()
        self.insertRow(number)
        for index, cell in enumerate(row["cells"]):
            item = QTableWidgetItem()
            if row["bg"]:
                item.setBackground(QColor(row["bg"]))
            hint = _hint_of(cell)
            if hint:
                item.setToolTip(hint)
            self.setItem(number, index, item)
            self.setCellWidget(number, index, self._wrap(cell, index))
        self.fit_later()

    def _wrap(self, cell, index: int) -> QWidget:
        """Виджет ячейки с отступами; щелчки проходят сквозь него к таблице."""
        box = QWidget()
        last = len(self.columns) - 1
        layout = hbox(
            box, margins=(16 if index == 0 else 8, 7, 16 if index == last else 8, 7)
        )
        layout.addWidget(self._make(cell), 1)
        if not (isinstance(cell, tuple) and cell[0] == "buttons"):
            box.setAttribute(Qt.WA_TransparentForMouseEvents)
        return box

    def _make(self, cell, in_line: bool = False) -> QWidget:
        """Создаёт виджет для одной ячейки или её части."""
        if not isinstance(cell, tuple):
            cell = ("text", "" if cell is None else str(cell))
        kind = cell[0]
        if kind in ("text", "bold", "muted", "small", "sub"):
            kinds = {"bold": "bold", "muted": "muted", "small": "caps", "sub": "small"}
            return label(cell[1], kinds.get(kind), wrap=not in_line)
        if kind == "pill":
            return Pill(cell[1], cell[2])
        if kind == "seats":
            return self._seats(cell[1], cell[2])
        if kind == "buttons":
            box = QWidget()
            layout = hbox(box, spacing=6)
            for text, style, command, enabled, *hint in cell[1]:
                widget = button(text, command, style, small=True)
                widget.setEnabled(enabled)
                if not enabled and hint:
                    box.setToolTip(hint[0])  # у неактивной кнопки подсказки нет
                layout.addWidget(widget)
            layout.addStretch()
            return box
        box = QWidget()  # line или stack
        layout = hbox(box, spacing=4) if kind == "line" else vbox(box, spacing=3)
        if kind == "stack":
            layout.addStretch()  # части — посередине строки по высоте
        for index, part in enumerate(cell[1]):
            # серые строки под названием в stack — мелким шрифтом, как в образцах
            if kind == "stack" and index > 0 and part[0] == "muted":
                part = ("sub", part[1])
            layout.addWidget(self._make(part, in_line=kind == "line"))
        layout.addStretch()
        return box

    def _seats(self, taken: int, free: int) -> QWidget:
        """Полоска заполненности мест и подпись «3 из 4» / «мест нет»."""
        box = QWidget()
        layout = hbox(box, spacing=8)
        layout.addWidget(SeatsBar(taken, taken + free))
        text = label(f"{free} из {taken + free}" if free > 0 else "мест нет")
        if free <= 0:
            text.setStyleSheet(f"color: {c('seat_taken')}; font-weight: 600;")
        layout.addWidget(text)
        layout.addStretch()
        return box

    def fit_later(self, *_args) -> None:
        """Пересчитать высоту строк чуть позже (когда изменится ширина)."""
        self.fit_timer.start(0)

    def fit_rows(self) -> None:
        """Подгоняет ширину узких столбцов и высоту строк под содержимое.

        Узкий (не растягиваемый) столбец становится шире заданного, если
        в него не помещается заголовок или таблетка статуса.
        """
        head = self.horizontalHeader()
        for column, (title, width, stretch) in enumerate(self.columns):
            if stretch:
                continue
            need = head.fontMetrics().horizontalAdvance(title + " ▼") + 34
            for number in range(self.rowCount()):
                widget = self.cellWidget(number, column)
                if widget is not None:
                    need = max(need, widget.minimumSizeHint().width())
            if self.columnWidth(column) != max(width, need):
                self.setColumnWidth(column, max(width, need))
        for number in range(self.rowCount()):
            height = 38
            for column in range(self.columnCount()):
                widget = self.cellWidget(number, column)
                if widget is None:
                    continue
                width = self.columnWidth(column)
                if widget.hasHeightForWidth():
                    height = max(height, widget.heightForWidth(width))
                else:
                    height = max(height, widget.sizeHint().height())
            self.setRowHeight(number, height)

    def resizeEvent(self, event):
        """При изменении размера таблицы пересчитывает высоту строк."""
        super().resizeEvent(event)
        self._place_empty()
        self.fit_later()

    def _place_empty(self) -> None:
        """Подпись пустой таблицы — посередине верхней части."""
        self.empty.setGeometry(0, 30, self.viewport().width(), 90)

    # ------------------------------------------------------------ выбор

    def select(self, row_id, notify: bool = True) -> None:
        """Выбирает строку и подсвечивает её.

        Args:
            row_id: id строки; None — снять выделение.
            notify: Вызывать ли on_select.
        """
        if row_id is not None and row_id not in self.rows:
            return
        self.quiet = True
        if row_id is None:
            self.clearSelection()
        else:
            self.selectRow(self.order.index(row_id))
        self.quiet = False
        self.selected = row_id
        if notify and row_id is not None and self.on_select:
            self.on_select(row_id)

    def _selection_changed(self) -> None:
        """Пользователь выбрал строку мышью."""
        if self.quiet:
            return
        chosen = self.selectionModel().selectedRows()
        row_id = self.order[chosen[0].row()] if chosen else None
        if row_id == self.selected:
            return
        self.selected = row_id
        if row_id is not None and self.on_select:
            self.on_select(row_id)

    def _double(self, number: int, _column: int) -> None:
        """Двойной щелчок по строке."""
        if self.on_double and number < len(self.order):
            self.on_double(self.order[number])

    def _paint_row(self, number: int, color) -> None:
        """Меняет фон строки (подсветка под курсором мыши)."""
        if number is None or number >= self.rowCount():
            return
        for column in range(self.columnCount()):
            item = self.item(number, column)
            if item is not None:
                item.setBackground(QColor(color) if color else QColor(0, 0, 0, 0))

    def _hover(self, number: int, _column: int) -> None:
        """Подсвечивает строку под курсором (цветные строки не трогает)."""
        if number == self.hovered:
            return
        self._unhover()
        self.hovered = number
        if self.rows[self.order[number]]["bg"] is None:
            self._paint_row(number, c("hover_row"))

    def _unhover(self) -> None:
        """Возвращает строке под курсором её обычный цвет."""
        if self.hovered is not None and self.hovered < len(self.order):
            self._paint_row(self.hovered, self.rows[self.order[self.hovered]]["bg"])
        self.hovered = None

    def leaveEvent(self, event):
        """Курсор ушёл с таблицы — подсветка снимается."""
        self._unhover()
        super().leaveEvent(event)

    # ------------------------------------------------------------ сортировка

    def sort_by(self, index: int) -> None:
        """Сортирует строки по столбцу; повторный щелчок — в обратном порядке.

        Args:
            index: Номер столбца.
        """
        self.sort_reverse = self.sort_column == index and not self.sort_reverse
        self.sort_column = index
        self.order.sort(
            key=lambda row_id: _sort_key(self.rows[row_id]["values"][index]),
            reverse=self.sort_reverse,
        )
        selected = self.selected
        self.quiet = True
        self.setRowCount(0)
        self.quiet = False
        self.hovered = None
        for row_id in self.order:
            self._insert(row_id)
        self.select(selected, notify=False)
        for number, (title, _, _) in enumerate(self.columns):
            arrow = (" ▼" if self.sort_reverse else " ▲") if number == index else ""
            self.horizontalHeaderItem(number).setText(title + arrow)


def _hint_of(cell):
    """Подсказка для ячейки: по первой метке, у которой она есть."""
    if not isinstance(cell, tuple):
        return None
    if cell[0] in ("line", "stack"):
        for part in cell[1]:
            hint = _hint_of(part)
            if hint:
                return hint
        return None
    if cell[0] == "seats":
        return f"Занято {cell[1]} из {cell[1] + cell[2]} мест"
    if cell[0] in ("text", "bold", "muted", "small", "sub", "pill"):
        return hint_for(cell[1])
    return None


def _cell_text(cell) -> str:
    """Возвращает текст ячейки для сортировки."""
    if not isinstance(cell, tuple):
        return "" if cell is None else str(cell)
    if cell[0] in ("line", "stack"):
        return " ".join(_cell_text(part) for part in cell[1])
    if cell[0] == "seats":
        return str(cell[2])  # по числу свободных мест
    if cell[0] == "buttons":
        return ""
    return str(cell[1])


def _sort_key(value):
    """Ключ сортировки: числа по числу, даты в формате БД и текст — по алфавиту."""
    if isinstance(value, (int, float)):
        return (0, value, "")
    return (1, 0, str(value).lower())
