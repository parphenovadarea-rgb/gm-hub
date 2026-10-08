"""Таблицы и списки в стиле макетов Figma.

Стандартная таблица Tkinter (Treeview) выглядит как таблица Excel: сетка,
одна строка текста в ячейке, нельзя поставить цветной статус или кнопку.
Поэтому строки здесь собираются из обычных виджетов:

- строки разделены тонкой линией, без вертикальной сетки;
- в ячейке может быть жирное название с серой подписью;
- статусы — скруглённые «таблетки» (рисуются на Canvas);
- в строке могут быть кнопки («Подтвердить», «Отклонить»);
- выбранная строка подсвечивается, по заголовку столбца — сортировка.

Ячейка описывается простым значением:
    "текст"                          — обычный текст;
    ("bold", "текст")                — жирный;
    ("muted", "текст")               — серый;
    ("small", "ТЕКСТ")               — мелкий серый (подпись категории);
    ("pill", "Подтверждена", "ok")   — таблетка: ok, warn, bad, grey, chip;
    ("seats", занято, свободно)      — квадратики мест ■■□□;
    ("line", [часть, часть, ...])    — части в одну строку;
    ("stack", [часть, часть, ...])   — части друг под другом;
    ("buttons", [(текст, стиль, функция, активна), ...]) — кнопки.
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from gm_hub.ui.theme import COLORS as C
from gm_hub.ui.common import (
    px,
    ACCENT,
    BG,
    FONT,
    FONT_BOLD,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    GREEN_SOFT,
    HEAD,
    INK,
    LINE,
    MUTED,
    RED,
    RED_SOFT,
    YELLOW,
    YELLOW_SOFT,
    Tooltip,
)

ROW_LINE = C["row_line"]  # разделитель строк
PENDING_ROW = C["pending_row"]  # строка с новой заявкой
SOON_ROW = C["soon_row"]  # сессия скоро — запись истекает (п. 4.1.6 ТЗ)
SELECTED_ROW = C["selected_row"]  # выбранная строка — с полоской слева
HOVER_ROW = C["hover_row"]  # строка под курсором мыши

# Цвета таблеток: (фон, текст, рамка)
PILLS = {
    "ok": (GREEN_SOFT, C["green_text"], None),
    "warn": (YELLOW_SOFT, YELLOW, None),
    "bad": (RED_SOFT, RED, None),
    "grey": (HEAD, MUTED, None),
    "chip": (BG, INK, LINE),
}

# Статусы из БД -> вид таблетки
STATUS_PILL = {
    "PENDING": "warn",
    "CONFIRMED": "ok",
    "REJECTED": "bad",
    "PLANNED": "ok",
    "CLOSED": "grey",
    "CANCELLED": "bad",
}


class Pill(tk.Canvas):
    """Скруглённая таблетка с текстом (статус, участник в «Составе»)."""

    def __init__(self, parent, text: str, kind: str = "grey", bg: str = BG):
        """Рисует таблетку.

        Args:
            parent: Родительский виджет.
            text: Текст.
            kind: Вид из словаря PILLS.
            bg: Цвет фона вокруг таблетки (цвет строки).
        """
        font = tkfont.Font(font=FONT_SMALL_BOLD if kind != "chip" else FONT_SMALL)
        width = font.measure(text) + 18
        height = font.metrics("linespace") + 4
        super().__init__(
            parent, width=width, height=height, bg=bg, highlightthickness=0, bd=0
        )
        fill, color, outline = PILLS[kind]
        r = height // 2
        # скруглённый прямоугольник = два круга по краям + прямоугольник
        for x in (0, width - 2 * r - 1):
            self.create_oval(
                x, 0, x + 2 * r, height - 1, fill=fill, outline=outline or fill
            )
        self.create_rectangle(r, 0, width - r - 1, height - 1, fill=fill, width=0)
        if outline:
            self.create_line(r, 0, width - r, 0, fill=outline)
            self.create_line(r, height - 1, width - r, height - 1, fill=outline)
        self.create_text(width // 2, height // 2, text=text, fill=color, font=font)


def _rgb(color: str) -> tuple:
    """«#285331» -> (40, 83, 49)."""
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


def _mix(back: tuple, front: tuple, share: float) -> tuple:
    """Смешивает два цвета: share — доля верхнего цвета (0..1)."""
    return tuple(round(b + (f - b) * share) for b, f in zip(back, front))


def _capsule(x: int, y: int, length: float, h: int) -> float:
    """Какая доля пикселя (x, y) закрыта капсулой длиной length и высотой h.

    Пиксель делится на 4×4 точки: так края капсулы получаются гладкими
    (сглаживание), а не «ступеньками».
    """
    r = h / 2
    inside = 0
    for i in range(4):
        for j in range(4):
            sx, sy = x + (i + 0.5) / 4, y + (j + 0.5) / 4
            cx = min(max(sx, r), length - r)  # ближайшая точка оси капсулы
            inside += (sx - cx) ** 2 + (sy - r) ** 2 <= r * r
    return inside / 16


_BAR_CACHE = {}  # одинаковые полоски рисуются один раз


def bar_image(widget, w: int, h: int, filled: int, bg: str, track: str, fill: str):
    """Картинка полоски мест со сглаженными скруглёнными концами.

    Args:
        widget: Любой виджет окна (картинка принадлежит этому окну Tk).
        w, h: Размер в пикселях.
        filled: Длина закрашенной части в пикселях.
        bg, track, fill: Цвета фона, пустой дорожки и занятой части.

    Returns:
        tk.PhotoImage.
    """
    key = (id(widget.tk), w, h, filled, bg, track, fill)
    if key not in _BAR_CACHE:
        back, line, front = _rgb(bg), _rgb(track), _rgb(fill)
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                color = _mix(back, line, _capsule(x, y, w, h))
                if filled:
                    color = _mix(color, front, _capsule(x, y, max(filled, h), h))
                row.append("#%02x%02x%02x" % color)
            rows.append("{" + " ".join(row) + "}")
        image = tk.PhotoImage(master=widget, width=w, height=h)
        image.put(" ".join(rows))
        _BAR_CACHE[key] = image
    return _BAR_CACHE[key]


class SeatsBar(tk.Label):
    """Полоска заполненности мест: зеленеет по мере записи, полная — тёмная."""

    def __init__(self, parent, taken: int, total: int, bg: str = BG, width: int = 70):
        """Рисует полоску.

        Args:
            parent: Родительский виджет.
            taken: Сколько мест занято (подтверждённые заявки).
            total: Лимит мест.
            bg: Цвет фона вокруг полоски.
            width: Ширина полоски для экрана 100 %.
        """
        w, h = px(width), px(8)
        filled = round(w * min(taken, total) / total) if total else 0
        color = C["seat_taken"] if taken >= total else C["green_text"]
        self.shape = (w, h, filled)
        self.color = color
        self.image = bar_image(parent, w, h, filled, bg, LINE, color)
        super().__init__(parent, image=self.image, bg=bg, bd=0)
        Tooltip(self, f"Занято {taken} из {total} мест")

    def configure(self, cnf=None, **kw):
        """При смене фона (подсветка строки) перерисовывает и края полоски."""
        if "bg" in kw:
            self.image = bar_image(self, *self.shape, kw["bg"], LINE, self.color)
            kw["image"] = self.image
        return super().configure(cnf, **kw)

    config = configure


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


class RowTable(ttk.Frame):
    """Таблица или список строк в стиле макетов.

    Заголовок и все строки лежат в одной общей сетке (grid), поэтому
    столбцы всегда ровные, какой бы длины ни был текст в ячейках.
    Под каждой строкой — подложка на всю ширину: она даёт цвет строки
    (жёлтый у новой заявки, серо-зелёный у выбранной).

    Attributes:
        selected: id выбранной строки или None.
    """

    def __init__(
        self, parent, columns, header=True, on_select=None, border=True, on_double=None
    ):
        """Создаёт пустую таблицу.

        Args:
            parent: Родительский виджет.
            columns: Список (заголовок, ширина, растягивать ли столбец).
            header: Показывать ли строку заголовков.
            on_select: Функция, вызываемая с id строки при её выборе.
            border: Рамка вокруг таблицы (внутри карточки не нужна).
            on_double: Функция, вызываемая с id строки при двойном щелчке.
        """
        super().__init__(
            parent, style="Card.TFrame" if border else "TFrame", padding=px(5)
        )
        self.columns = columns
        self.on_select = on_select
        self.on_double = on_double
        self.selected = None
        self.rows = {}  # id -> словарь: подложка, ячейки, линия, цвет, сортировка
        self.sort_column = None
        self.sort_reverse = False
        self.head_labels = []
        self.hovered = None  # id строки под курсором

        # Прокрутка: сетка лежит в рамке внутри Canvas, крутится колесом мыши.
        # Ширина области = сумма столбцов с отступами (иначе у Canvas свой размер).
        width = px(sum(w for _, w, _ in columns) + 16 * len(columns) + 16)
        self.canvas = tk.Canvas(
            self, bg=BG, highlightthickness=0, bd=0, width=width, height=100
        )
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=BG)
        window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfig(window, width=e.width)
        )
        self.body.bind("<Configure>", lambda e: self._update_scroll())
        self.canvas.bind("<Enter>", lambda e: self._wheel(True))
        self.canvas.bind("<Leave>", lambda e: (self._wheel(False), self._hover(None)))
        for index, (_, width, stretch) in enumerate(columns):
            self.body.columnconfigure(
                index, minsize=px(width), weight=1 if stretch else 0
            )

        span = len(columns)
        self.first_row = 0
        if header:
            # серая полоса заголовка со скруглёнными верхними углами
            ttk.Frame(self.body, style="TableHead.TFrame").grid(
                row=0, column=0, columnspan=span, sticky="nsew"
            )
            for index, (title, _, _) in enumerate(columns):
                label = tk.Label(
                    self.body, text=title, bg=HEAD, fg=INK, font=FONT_BOLD, anchor="w"
                )
                label.grid(row=0, column=index, sticky="ew", padx=self._pad(index))
                label.config(pady=px(6), cursor="hand2")
                label.bind("<Button-1>", lambda e, i=index: self.sort_by(i))
                self.head_labels.append(label)
            tk.Frame(self.body, bg=LINE, height=1).grid(
                row=1, column=0, columnspan=span, sticky="ew"
            )
            self.first_row = 2
        # Подсказка в пустой таблице: что сделать, чтобы здесь появились данные.
        self.empty = tk.Label(
            self.body, bg=BG, fg=MUTED, font=FONT, pady=px(40), justify="center"
        )

    def _pad(self, index: int) -> tuple:
        """Отступы ячейки: у первой и последней колонки побольше."""
        last = len(self.columns) - 1
        return px((16 if index == 0 else 8, 16 if index == last else 8))

    def _update_scroll(self) -> None:
        """Обновляет область прокрутки после изменения строк."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _wheel(self, on: bool) -> None:
        """Включает прокрутку колесом мыши, пока курсор над таблицей."""
        if on:
            self.canvas.bind_all(
                "<MouseWheel>",
                lambda e: self.canvas.yview_scroll(-e.delta // 120, "units"),
            )
        else:
            self.canvas.unbind_all("<MouseWheel>")

    def clear(self, empty_text: str = "") -> None:
        """Удаляет все строки.

        Args:
            empty_text: Подпись, которая показывается, пока строк нет.
        """
        for row in self.rows.values():
            for widget in [row["back"], row["bar"], row["line"]] + row["cells"]:
                widget.destroy()
        self.rows = {}
        self.selected = None
        self.hovered = None
        self.empty.config(text=empty_text)
        if empty_text:
            self.empty.grid(row=self.first_row, column=0, columnspan=len(self.columns))
        else:
            self.empty.grid_remove()
        self.canvas.yview_moveto(0)

    def add(self, row_id, cells, sort=None, highlight=False) -> None:
        """Добавляет строку в конец таблицы.

        Args:
            row_id: id записи в БД — по нему строку потом выбирают.
            cells: Ячейки по числу столбцов (формат — в описании модуля).
            sort: Значения для сортировки по столбцам (по умолчанию — текст).
            highlight: Подсветка строки: True — жёлтая (новая заявка),
                "soon" — зелёная (сессия скоро).
        """
        self.empty.grid_remove()
        bg = {True: PENDING_ROW, "soon": SOON_ROW}.get(highlight, BG)
        back = tk.Frame(self.body, bg=bg)  # подложка — цвет всей строки
        bar = tk.Frame(self.body, bg=bg, width=px(4))  # полоска выбранной строки
        widgets = []
        for index, (cell, (_, width, _)) in enumerate(zip(cells, self.columns)):
            widgets.append(self._make(self.body, cell, bg, width - 16))
        line = tk.Frame(self.body, bg=ROW_LINE, height=1)
        values = sort if sort is not None else [_cell_text(c) for c in cells]
        row = {"back": back, "bar": bar, "cells": widgets, "line": line, "bg": bg}
        row["values"] = values
        self.rows[row_id] = row
        self._place(row, len(self.rows) - 1)
        for widget in [back, bar] + widgets:
            self._bind_click(widget, row_id)
            self._bind_hover(widget, row_id)

    def _place(self, row, position: int) -> None:
        """Ставит строку в сетку на место position (считая от первой строки)."""
        grid_row = self.first_row + position * 2
        span = len(self.columns)
        row["back"].grid(row=grid_row, column=0, columnspan=span, sticky="nsew")
        row["back"].lower()  # подложка под ячейками
        row["bar"].grid(row=grid_row, column=0, sticky="nsw")
        for index, widget in enumerate(row["cells"]):
            widget.grid(
                row=grid_row,
                column=index,
                sticky="w",
                padx=self._pad(index),
                pady=px(6),
            )
        row["line"].grid(row=grid_row + 1, column=0, columnspan=span, sticky="ew")

    def _make(self, parent, cell, bg, width):
        """Создаёт виджет для одной ячейки или её части."""
        if not isinstance(cell, tuple):
            cell = ("text", "" if cell is None else str(cell))
        kind = cell[0]
        if kind in ("text", "bold", "muted", "small", "sub"):
            fonts = {"bold": FONT_BOLD, "small": FONT_SMALL_BOLD, "sub": FONT_SMALL}
            font = fonts.get(kind, FONT)
            color = MUTED if kind in ("muted", "small", "sub") else INK
            label = tk.Label(
                parent,
                text=cell[1],
                bg=bg,
                fg=color,
                font=font,
                anchor="w",
                justify="left",
                wraplength=px(max(width, 60)),
            )
            if hint_for(cell[1]):
                Tooltip(label, hint_for(cell[1]))
            return label
        if kind == "pill":
            pill = Pill(parent, cell[1], cell[2], bg)
            if hint_for(cell[1]):
                Tooltip(pill, hint_for(cell[1]))
            return pill
        if kind == "seats":
            return self._seats(parent, cell[1], cell[2], bg)
        if kind == "buttons":
            # кнопка: (текст, стиль, функция, активна[, подсказка если неактивна])
            box = tk.Frame(parent, bg=bg)
            for text, style, command, enabled, *hint in cell[1]:
                button = ttk.Button(box, text=text, style=style, command=command)
                if not enabled:
                    button.state(["disabled"])
                    if hint:
                        Tooltip(button, hint[0])
                button.pack(side="left", padx=px((0, 6)))
            return box
        box = tk.Frame(parent, bg=bg)  # line или stack
        for index, part in enumerate(cell[1]):
            # серые строки под названием в stack — мелким шрифтом, как в образцах
            if kind == "stack" and index > 0 and part[0] == "muted":
                part = ("sub", part[1])
            widget = self._make(box, part, bg, width)
            if kind == "line":
                widget.pack(side="left", padx=px((0, 3)))
            else:
                widget.pack(anchor="w")
        return box

    def _seats(self, parent, taken: int, free: int, bg):
        """Полоска заполненности мест и подпись «3 из 4» / «мест нет»."""
        box = tk.Frame(parent, bg=bg)
        SeatsBar(box, taken, taken + free, bg).pack(side="left")
        text = f"{free} из {taken + free}" if free > 0 else "мест нет"
        tk.Label(
            box,
            text=text,
            bg=bg,
            fg=C["seat_taken"] if free <= 0 else INK,
            font=FONT_BOLD if free <= 0 else FONT,
        ).pack(side="left", padx=px((8, 0)))
        return box

    def _bind_click(self, widget, row_id) -> None:
        """Щелчок по любой части строки (кроме кнопок) выбирает строку."""
        if isinstance(widget, ttk.Button):
            return
        widget.bind("<Button-1>", lambda e: self.select(row_id))
        if self.on_double:
            widget.bind("<Double-Button-1>", lambda e: self.on_double(row_id))
        for child in widget.winfo_children():
            self._bind_click(child, row_id)

    def _paint(self, widget, bg) -> None:
        """Перекрашивает фон части строки вместе со всем, что внутри."""
        if isinstance(widget, ttk.Button):
            return
        widget.config(bg=bg)
        for child in widget.winfo_children():
            self._paint(child, bg)

    def _paint_row(self, row, bg, bar=None) -> None:
        """Перекрашивает всю строку: подложку, ячейки и полоску слева."""
        for widget in [row["back"]] + row["cells"]:
            self._paint(widget, bg)
        row["bar"].config(bg=bar or bg)

    def _bind_hover(self, widget, row_id) -> None:
        """Наведение мыши на любую часть строки подсвечивает строку."""
        widget.bind("<Enter>", lambda e: self._hover(row_id), add="+")
        for child in widget.winfo_children():
            self._bind_hover(child, row_id)

    def _hover(self, row_id) -> None:
        """Подсвечивает строку под курсором (выбранную и цветные не трогает)."""
        if row_id == self.hovered:
            return
        old = self.rows.get(self.hovered)
        if old and self.hovered != self.selected:
            self._paint_row(old, old["bg"])
        self.hovered = row_id
        new = self.rows.get(row_id)
        if new and row_id != self.selected and new["bg"] == BG:
            self._paint_row(new, HOVER_ROW)

    def select(self, row_id, notify: bool = True) -> None:
        """Выбирает строку и подсвечивает её.

        Args:
            row_id: id строки; None — снять выделение.
            notify: Вызывать ли on_select.
        """
        if row_id is not None and row_id not in self.rows:
            return
        if self.selected in self.rows:
            old = self.rows[self.selected]
            self._paint_row(old, old["bg"])
        self.selected = row_id
        if row_id is None:
            return
        self._paint_row(self.rows[row_id], SELECTED_ROW, bar=ACCENT)
        if notify and self.on_select:
            self.on_select(row_id)

    def sort_by(self, index: int) -> None:
        """Сортирует строки по столбцу; повторный щелчок — в обратном порядке.

        Args:
            index: Номер столбца.
        """
        self.sort_reverse = self.sort_column == index and not self.sort_reverse
        self.sort_column = index
        order = sorted(
            self.rows.values(),
            key=lambda row: _sort_key(row["values"][index]),
            reverse=self.sort_reverse,
        )
        for position, row in enumerate(order):
            self._place(row, position)
        for i, label in enumerate(self.head_labels):
            title = self.columns[i][0]
            arrow = (" ▼" if self.sort_reverse else " ▲") if i == index else ""
            label.config(text=title + arrow)


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
