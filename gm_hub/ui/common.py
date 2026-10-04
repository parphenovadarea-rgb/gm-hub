"""Общие элементы интерфейса по макетам Figma (п. 4.1.13 ТЗ).

Здесь цвета, стили ttk, шапка окна со вкладками, таблицы, баннеры
и карточки выбора — всё, что повторяется в нескольких окнах.
"""

import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timedelta
from tkinter import ttk

from gm_hub.config import DATETIME_FORMAT, SHOW_FORMAT

# Палитра из макетов Figma.
ACCENT = "#285331"  # тёмно-зелёные кнопки
ACCENT_HOVER = "#1e4026"
ACCENT_SOFT = "#c3cfc6"  # выбранная строка, выбранный фильтр
GREEN_SOFT = "#e3f3e6"  # успех, выбранная карточка
BG = "#ffffff"
BG_SOFT = "#f7f8fa"
HEAD = "#eef0f4"  # заголовки таблиц
LINE = "#d6d9e2"
INK = "#1b1d26"
MUTED = "#5f6475"
RED = "#a1362c"
RED_SOFT = "#fbe7e4"
YELLOW = "#8a5a00"
YELLOW_SOFT = "#fff1d1"

# Подсветка строк таблиц (п. 4.1.6 ТЗ).
ROW_COLORS = {
    "soon": "#f1f6f2",  # сессия скоро, запись истекает
    "PENDING": YELLOW_SOFT,  # новая заявка
    "CONFIRMED": "#f1f8f2",
    "REJECTED": "#fdf3f2",
}

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_LOGO = ("Georgia", 14, "bold")
FONT_TITLE = ("Georgia", 20, "bold")


def setup_style(root: tk.Tk) -> None:
    """Настраивает единый вид кнопок, полей, таблиц и вкладок.

    Args:
        root: Главное окно.
    """
    root.configure(bg=BG)
    # Меняем стандартные шрифты Tk, а не option_add("*Font"):
    # иначе шрифт из базы опций перебивает шрифты стилей.
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
        tkfont.nametofont(name).configure(family=FONT[0], size=FONT[1])

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=INK, font=FONT, bordercolor=LINE)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Small.TLabel", foreground=MUTED, font=FONT_SMALL)
    style.configure("Bold.TLabel", font=FONT_BOLD)
    style.configure("Title.TLabel", font=FONT_TITLE)
    style.configure("Logo.TLabel", font=FONT_LOGO)
    style.configure("Green.TLabel", foreground=ACCENT, font=FONT_BOLD)

    # Кнопки: белая с рамкой, зелёная главная, белая с красным текстом.
    flat = {"lightcolor": BG, "darkcolor": BG, "bordercolor": LINE, "padding": (12, 5)}
    style.configure("TButton", background=BG, **flat)
    style.map("TButton", background=[("active", BG_SOFT)])
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="white",
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        font=FONT_BOLD,
        padding=(12, 5),
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", "#e4ebe5"), ("active", ACCENT_HOVER)],
        foreground=[("disabled", "#8fa596")],
        bordercolor=[("disabled", "#e4ebe5")],
        lightcolor=[("disabled", "#e4ebe5"), ("active", ACCENT_HOVER)],
        darkcolor=[("disabled", "#e4ebe5"), ("active", ACCENT_HOVER)],
    )
    style.configure("Danger.TButton", background=BG, foreground=RED, **flat)
    style.map("Danger.TButton", background=[("active", RED_SOFT)])

    # Вкладки-закладки в шапке и сегментные фильтры — это Radiobutton.
    style.configure(
        "Tab.Toolbutton",
        background=BG,
        foreground=MUTED,
        padding=(18, 8),
        bordercolor=BG,
        lightcolor=BG,
        darkcolor=BG,
        font=("Segoe UI", 11),
    )
    style.map(
        "Tab.Toolbutton",
        background=[("selected", BG_SOFT), ("active", BG_SOFT)],
        foreground=[("selected", INK)],
        bordercolor=[("selected", LINE)],
    )
    style.configure("Seg.Toolbutton", background=BG, padding=(12, 5), **_no_3d())
    style.map(
        "Seg.Toolbutton",
        background=[("selected", ACCENT_SOFT), ("active", BG_SOFT)],
        foreground=[("selected", ACCENT)],
    )

    style.configure(
        "TEntry", fieldbackground=BG, bordercolor=LINE, lightcolor=BG, padding=5
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", BG)])
    style.configure("TCombobox", fieldbackground=BG, background=BG, padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", BG)])
    style.configure("TSpinbox", fieldbackground=BG, background=BG, padding=4)
    style.configure("TCheckbutton", indicatorcolor=BG)
    style.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)])

    style.configure(
        "Treeview",
        background=BG,
        fieldbackground=BG,
        rowheight=30,
        bordercolor=LINE,
        lightcolor=BG,
        darkcolor=BG,
    )
    style.configure(
        "Treeview.Heading",
        background=HEAD,
        font=FONT_BOLD,
        bordercolor=LINE,
        lightcolor=HEAD,
        darkcolor=HEAD,
        padding=(6, 6),
    )
    style.map("Treeview.Heading", background=[("active", HEAD)])
    style.map("Treeview", background=[("selected", ACCENT_SOFT)])
    style.map("Treeview", foreground=[("selected", INK)])
    style.configure("Tall.Treeview", rowheight=48)
    style.configure("Header.TFrame", background=BG)
    style.configure("Line.TFrame", background=LINE)


def _no_3d() -> dict:
    """Параметры, убирающие объёмную рамку у кнопок темы clam."""
    return {"bordercolor": LINE, "lightcolor": BG, "darkcolor": BG}


def link(parent, text: str, command, color: str = RED) -> tk.Label:
    """Создаёт текстовую ссылку («Выйти», «Зарегистрироваться»).

    Args:
        parent: Родительский виджет.
        text: Текст ссылки.
        command: Функция без аргументов, вызывается по щелчку.
        color: Цвет текста.

    Returns:
        Метка, которая ведёт себя как ссылка.
    """
    label = tk.Label(parent, text=text, fg=color, bg=BG, cursor="hand2", font=FONT)
    label.bind("<Button-1>", lambda event: command())
    return label


def card(parent, title: str | None = None, note: str | None = None) -> ttk.Frame:
    """Создаёт белую карточку с тонкой рамкой, как панели в макетах.

    Args:
        parent: Родительский виджет.
        title: Заголовок карточки.
        note: Серая подпись справа от заголовка.

    Returns:
        Внутренняя рамка карточки, в неё кладутся поля.
        Саму карточку размещать через .master.
    """
    outer = tk.Frame(parent, bg=BG, highlightthickness=1, highlightbackground=LINE)
    head_label = None
    if title:
        head = ttk.Frame(outer, padding=(14, 10))
        head.pack(fill="x")
        head_label = ttk.Label(head, text=title, style="Bold.TLabel")
        head_label.pack(side="left")
        if note:
            ttk.Label(head, text=note, style="Small.TLabel").pack(side="right")
        ttk.Frame(outer, style="Line.TFrame", height=1).pack(fill="x")
    inner = ttk.Frame(outer, padding=14)
    inner.pack(fill="both", expand=True)
    inner.title_label = head_label  # чтобы менять заголовок карточки
    return inner


def segmented(parent, options, variable, command) -> ttk.Frame:
    """Создаёт переключатель-сегменты («Предстоящие | Прошедшие | …»).

    Args:
        parent: Родительский виджет.
        options: Список пар (подпись, значение).
        variable: Переменная Tk, куда пишется выбранное значение.
        command: Функция, вызываемая при переключении.

    Returns:
        Рамка с кнопками-сегментами.
    """
    frame = tk.Frame(parent, bg=LINE, padx=1, pady=1)
    for text, value in options:
        ttk.Radiobutton(
            frame,
            text=text,
            value=value,
            variable=variable,
            command=command,
            style="Seg.Toolbutton",
        ).pack(side="left", padx=(0, 1))
    return frame


class Banner(tk.Frame):
    """Цветная плашка с сообщением: ошибка (красная) или успех (зелёная)."""

    KINDS = {"error": ("!", RED_SOFT, RED), "ok": ("✓", GREEN_SOFT, ACCENT)}

    def __init__(self, parent, **pack_options):
        """Создаёт скрытую плашку.

        Args:
            parent: Родительский виджет.
            **pack_options: Как размещать плашку при показе (параметры pack).
        """
        super().__init__(parent, padx=12, pady=8)
        self.pack_options = pack_options
        self.icon = tk.Label(self, font=FONT_BOLD)
        self.icon.pack(side="left", padx=(0, 8))
        self.text = tk.Label(self, justify="left", anchor="w", font=FONT)
        self.text.pack(side="left", fill="x", expand=True)
        self.bind("<Configure>", lambda e: self.text.config(wraplength=e.width - 60))

    def show(self, message: str, kind: str = "error") -> None:
        """Показывает плашку.

        Args:
            message: Текст сообщения.
            kind: «error» или «ok».
        """
        icon, bg, fg = self.KINDS[kind]
        for widget in (self, self.icon, self.text):
            widget.config(bg=bg)
        self.icon.config(text=icon, fg=fg)
        self.text.config(text=message, fg=fg)
        self.pack(**self.pack_options)

    def hide(self) -> None:
        """Скрывает плашку."""
        self.pack_forget()


class ChoiceCards(ttk.Frame):
    """Выбор одного варианта карточками (роль при регистрации, персонаж)."""

    def __init__(self, parent, columns: int = 1):
        """Создаёт пустой список карточек.

        Args:
            parent: Родительский виджет.
            columns: Сколько карточек в одной строке.
        """
        super().__init__(parent)
        self.columns = columns
        self.value = None
        self.cards = {}

    def set_options(self, options) -> None:
        """Заменяет варианты выбора.

        Args:
            options: Список троек (значение, заголовок, подпись).
        """
        for child in self.winfo_children():
            child.destroy()
        self.cards = {}
        self.value = None
        for index, (value, title, subtitle) in enumerate(options):
            box = tk.Frame(self, bg=BG, highlightthickness=1, padx=10, pady=8)
            box.grid(
                row=index // self.columns,
                column=index % self.columns,
                sticky="nsew",
                padx=(0, 8) if index % self.columns < self.columns - 1 else 0,
                pady=(0, 8),
            )
            mark = tk.Label(box, font=("Segoe UI", 13), bg=BG)
            mark.pack(side="left", padx=(0, 8))
            texts = tk.Frame(box, bg=BG)
            texts.pack(side="left", fill="x")
            tk.Label(texts, text=title, font=FONT_BOLD, bg=BG, anchor="w").pack(
                fill="x"
            )
            tk.Label(
                texts, text=subtitle, fg=MUTED, bg=BG, anchor="w", justify="left"
            ).pack(fill="x")
            parts = [box, mark, texts] + list(texts.winfo_children())
            for widget in parts:
                widget.bind("<Button-1>", lambda e, v=value: self.select(v))
                widget.config(cursor="hand2")
            self.cards[value] = (box, mark, parts)
        for column in range(self.columns):
            self.columnconfigure(column, weight=1)
        self._paint()

    def select(self, value) -> None:
        """Выбирает вариант.

        Args:
            value: Значение выбранного варианта.
        """
        self.value = value
        self._paint()

    def get(self):
        """Возвращает выбранное значение или None."""
        return self.value

    def _paint(self) -> None:
        """Перекрашивает карточки: выбранная — зелёная."""
        for value, (box, mark, parts) in self.cards.items():
            chosen = value == self.value
            bg = GREEN_SOFT if chosen else BG
            for widget in parts:
                widget.config(bg=bg)
            box.config(highlightbackground=ACCENT if chosen else LINE)
            mark.config(text="◉" if chosen else "○", fg=ACCENT if chosen else MUTED)


class MainFrame(ttk.Frame):
    """Окно кабинета: шапка с названием, вкладками-закладками и пользователем."""

    def __init__(self, app, tabs):
        """Создаёт шапку и вкладки.

        Args:
            app: Приложение (app.user, app.logout, app.show_profile).
            tabs: Список пар (название вкладки, класс вкладки).
        """
        super().__init__(app)
        self.app = app
        header = ttk.Frame(self, padding=(20, 12, 20, 0))
        header.pack(fill="x")
        ttk.Label(header, text="Game Master Hub", style="Logo.TLabel").pack(
            side="left", anchor="n", pady=(4, 0)
        )

        user = ttk.Frame(header)
        user.pack(side="right", anchor="n")
        ttk.Label(user, text=app.user["full_name"], style="Bold.TLabel").pack(
            anchor="e"
        )
        links = ttk.Frame(user)
        links.pack(anchor="e")
        role = "Мастер" if app.user["role"] == "GM" else "Игрок"
        ttk.Label(links, text=role, style="Muted.TLabel").pack(side="left")
        link(links, "Профиль", app.show_profile, color=ACCENT).pack(
            side="left", padx=(10, 0)
        )
        link(links, "Выйти", app.logout).pack(side="left", padx=(10, 0))

        self.current = tk.IntVar(value=0)
        self.tab_buttons = []
        bar = ttk.Frame(header)
        bar.pack(side="left", anchor="s", padx=(60, 0), pady=(16, 0))
        ttk.Frame(self, style="Line.TFrame", height=1).pack(fill="x")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.tabs = []
        for index, (title, tab_class) in enumerate(tabs):
            button = ttk.Radiobutton(
                bar,
                text=title,
                value=index,
                variable=self.current,
                command=self.show_tab,
                style="Tab.Toolbutton",
            )
            button.pack(side="left")
            self.tab_buttons.append(button)
            tab = tab_class(body, app)
            tab.grid(row=0, column=0, sticky="nsew")
            self.tabs.append(tab)
        self.show_tab()

    def show_tab(self, index: int | None = None) -> None:
        """Показывает вкладку и перечитывает её данные из БД.

        Args:
            index: Номер вкладки. None — текущая выбранная.
        """
        if index is not None:
            self.current.set(index)
        tab = self.tabs[self.current.get()]
        tab.tkraise()
        tab.refresh()
        self.on_tab_shown()

    def on_tab_shown(self) -> None:
        """Вызывается после смены вкладки; переопределяется в окнах."""

    def set_tab_title(self, index: int, title: str) -> None:
        """Меняет подпись вкладки, например «Заявки (3)».

        Args:
            index: Номер вкладки.
            title: Новая подпись.
        """
        self.tab_buttons[index].config(text=title)


def _sort_key(text: str):
    """Ключ сортировки: даты по дате, числа по числу, остальное по алфавиту."""
    text = text.lstrip("■□ ")
    try:
        return (0, datetime.strptime(text, SHOW_FORMAT).strftime(DATETIME_FORMAT))
    except ValueError:
        pass
    try:
        return (1, float(text.split()[0]))  # «3 из 4» сортируется по 3
    except (ValueError, IndexError):
        return (2, text.lower())


def sort_table(tree: ttk.Treeview, column: str, reverse: bool = False) -> None:
    """Сортирует строки таблицы по столбцу (п. 4.1.6 ТЗ).

    Повторный щелчок по заголовку меняет порядок на обратный.

    Args:
        tree: Таблица.
        column: Идентификатор столбца.
        reverse: Сортировать по убыванию.
    """
    items = [(tree.set(iid, column), iid) for iid in tree.get_children()]
    items.sort(key=lambda pair: _sort_key(pair[0]), reverse=reverse)
    for index, (_, iid) in enumerate(items):
        tree.move(iid, "", index)
    tree.heading(column, command=lambda: sort_table(tree, column, not reverse))


def make_table(parent, columns, tall: bool = False) -> ttk.Treeview:
    """Создаёт таблицу с прокруткой и сортировкой по столбцам.

    Args:
        parent: Родительский виджет.
        columns: Список пар (заголовок, ширина).
        tall: Высокие строки — для ячеек в две строки (название и описание).

    Returns:
        Таблица Treeview. Рамку с ней нужно разместить через tree.master.
    """
    frame = tk.Frame(parent, bg=BG, highlightthickness=1, highlightbackground=LINE)
    ids = [f"c{i}" for i in range(len(columns))]
    tree = ttk.Treeview(
        frame,
        columns=ids,
        show="headings",
        selectmode="browse",
        style="Tall.Treeview" if tall else "Treeview",
    )
    for col_id, (title, width) in zip(ids, columns):
        tree.heading(
            col_id,
            text=title,
            anchor="w",
            command=lambda c=col_id: sort_table(tree, c),
        )
        tree.column(col_id, width=width, anchor="w")
    for tag, color in ROW_COLORS.items():
        tree.tag_configure(tag, background=color)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return tree


def clear_table(tree: ttk.Treeview) -> None:
    """Удаляет все строки таблицы.

    Args:
        tree: Таблица.
    """
    tree.delete(*tree.get_children())


def selected_id(tree: ttk.Treeview) -> int | None:
    """Возвращает id выбранной строки (id записи в БД).

    Args:
        tree: Таблица.

    Returns:
        id записи или None, если ничего не выбрано.
    """
    selection = tree.selection()
    return int(selection[0]) if selection else None


def seats_bar(free: int, max_players: int) -> str:
    """Рисует занятость мест квадратиками, как в макете: «■■□□ 2 из 4».

    Args:
        free: Свободных мест.
        max_players: Всего мест.

    Returns:
        Текст для ячейки таблицы.
    """
    text = f"{free} из {max_players}" if free > 0 else "мест нет"
    if max_players > 8:
        return text
    taken = max_players - free
    return "■" * taken + "□" * free + "  " + text


def is_soon(db_value: str, days: int = 3) -> bool:
    """Проверяет, что сессия начнётся в ближайшие дни (запись скоро закроется).

    Args:
        db_value: Дата сессии в формате БД.
        days: Сколько дней считать «скоро».

    Returns:
        True, если до сессии меньше days дней.
    """
    when = datetime.strptime(db_value, DATETIME_FORMAT)
    return datetime.now() <= when <= datetime.now() + timedelta(days=days)


def get_text(widget: tk.Text) -> str:
    """Возвращает текст многострочного поля.

    Args:
        widget: Поле Text.

    Returns:
        Текст без последнего перевода строки.
    """
    return widget.get("1.0", "end-1c").strip()


def set_text(widget: tk.Text, value: str | None) -> None:
    """Заменяет текст многострочного поля.

    Args:
        widget: Поле Text.
        value: Новый текст.
    """
    widget.delete("1.0", "end")
    widget.insert("1.0", value or "")


def make_text(parent, height: int = 5) -> tk.Text:
    """Создаёт многострочное поле в общем стиле.

    Args:
        parent: Родительский виджет.
        height: Высота в строках.

    Returns:
        Поле Text.
    """
    return tk.Text(
        parent,
        height=height,
        width=40,
        wrap="word",
        relief="flat",
        highlightthickness=1,
        highlightbackground=LINE,
        highlightcolor=ACCENT,
        padx=8,
        pady=6,
        font=FONT,
        bg=BG,
    )


def field(parent, label: str) -> ttk.Label:
    """Создаёт подпись над полем ввода, как в макетах.

    Args:
        parent: Родительский виджет.
        label: Текст подписи.

    Returns:
        Метка (уже размещена через pack).
    """
    widget = ttk.Label(parent, text=label, style="Muted.TLabel")
    widget.pack(anchor="w", pady=(8, 2))
    return widget
