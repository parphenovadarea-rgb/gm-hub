"""Общие элементы интерфейса по макетам Figma (п. 4.1.13 ТЗ).

Здесь цвета, стили ttk, шапка окна со вкладками, таблицы, баннеры
и карточки выбора — всё, что повторяется в нескольких окнах.
"""

import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import ttk

from gm_hub.config import DATETIME_FORMAT

# Палитра из макетов Figma.
ACCENT = "#285331"  # тёмно-зелёные кнопки
ACCENT_HOVER = "#1e4026"
ACCENT_SOFT = "#c3cfc6"  # выбранная строка, выбранный фильтр
GREEN_SOFT = "#e3f3e6"  # успех, выбранная карточка
BG = "#ffffff"
BG_SOFT = "#f7f8fa"
PAGE = BG_SOFT  # фон страницы под карточками
HEAD = "#eef0f4"  # заголовки таблиц
LINE = "#d6d9e2"
INK = "#1b1d26"
MUTED = "#5f6475"
RED = "#a1362c"
RED_SOFT = "#fbe7e4"
YELLOW = "#8a5a00"
YELLOW_SOFT = "#fff1d1"

# Масштаб экрана Windows (100 %, 125 %, 150 % ...). Программа сообщает Windows,
# что сама учитывает масштаб (см. app.make_dpi_aware) — тогда текст чёткий,
# а не растянутый картинкой. Шрифты в пунктах Tk масштабирует сам, а размеры
# в пикселях (отступы, ширина столбцов) пересчитывает функция px().
SCALE = 1.0


def px(value):
    """Переводит размер «для экрана 100 %» в пиксели текущего экрана.

    Args:
        value: Число или кортеж чисел (например, отступы (12, 4)).

    Returns:
        Число или кортеж, умноженные на масштаб экрана.
    """
    if isinstance(value, tuple):
        return tuple(round(v * SCALE) for v in value)
    return round(value * SCALE)


# Размеры как в макетах Figma: основной текст 15 px, подписи 13 px.
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI Semibold", 11)
FONT_SMALL = ("Segoe UI", 10)
FONT_SMALL_BOLD = ("Segoe UI Semibold", 10)
FONT_LOGO = ("Georgia", 15, "bold")
FONT_TITLE = ("Georgia", 20, "bold")


def setup_style(root: tk.Tk) -> None:
    """Настраивает единый вид кнопок, полей, таблиц и вкладок.

    Args:
        root: Главное окно.
    """
    global SCALE
    SCALE = root.winfo_fpixels("1i") / 96  # 96 точек на дюйм — это масштаб 100 %
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
    style.configure("Field.TLabel", foreground=MUTED, font=FONT_SMALL_BOLD)
    style.configure(
        "PageField.TLabel", background=PAGE, foreground=MUTED, font=FONT_SMALL_BOLD
    )
    style.configure("Caps.TLabel", foreground=MUTED, font=FONT_SMALL_BOLD)
    style.configure("Bold.TLabel", font=FONT_BOLD)
    style.configure("Title.TLabel", font=FONT_TITLE)
    style.configure("Logo.TLabel", font=FONT_LOGO)
    style.configure("Green.TLabel", foreground=ACCENT, font=FONT_BOLD)

    # Кнопки: белая с рамкой, зелёная главная, белая с красным текстом.
    # Скруглённые углы — это картинки из папки img, растянутые по краям.
    rounded_button(style, "TButton", "button", hover="button_hover")
    rounded_button(
        style,
        "Accent.TButton",
        "accent",
        hover="accent_hover",
        disabled="accent_disabled",
    )
    rounded_button(style, "Danger.TButton", "button", hover="danger_hover")
    style.configure("TButton", padding=px((12, 4)))
    style.configure(
        "Accent.TButton", foreground="white", font=FONT_BOLD, padding=px((12, 4))
    )
    style.map("Accent.TButton", foreground=[("disabled", "#8fa596")])
    style.configure("Danger.TButton", foreground=RED, padding=px((12, 4)))
    # Компактные кнопки внутри строк таблицы («Подтвердить», «Отклонить»).
    rounded_button(
        style,
        "Small.Accent.TButton",
        "accent",
        hover="accent_hover",
        disabled="accent_disabled",
    )
    rounded_button(style, "Small.Danger.TButton", "button", hover="danger_hover")
    rounded_button(style, "Small.TButton", "button", hover="button_hover")
    style.configure("Small.TButton", font=FONT_SMALL, padding=px((9, 2)))
    style.configure(
        "Small.Accent.TButton", foreground="white", font=FONT_SMALL, padding=px((9, 2))
    )
    style.map("Small.Accent.TButton", foreground=[("disabled", "#8fa596")])
    style.configure(
        "Small.Danger.TButton", foreground=RED, font=FONT_SMALL, padding=px((9, 2))
    )

    # Скруглённые серые рамки панелей: карточки, таблицы, фильтры, выбор.
    rounded_frame(style, "Card.TFrame", "card")
    rounded_frame(style, "Choice.TFrame", "choice")
    rounded_frame(style, "ChoiceOn.TFrame", "choice_on")

    # Вкладки-закладки в шапке и сегментные фильтры — это Radiobutton.
    style.configure(
        "Tab.Toolbutton",
        background=BG,
        foreground=MUTED,
        padding=px((16, 7)),
        bordercolor=BG,
        lightcolor=BG,
        darkcolor=BG,
        font=FONT_BOLD,
    )
    style.map(
        "Tab.Toolbutton",
        foreground=[("selected", INK)],
    )
    # Выбранная вкладка — закладка со скруглёнными верхними углами.
    style.element_create(
        "Tab.rounded",
        "image",
        image("tab_off"),
        ("selected", image("tab_on")),
        ("active", image("tab_on")),
        border=12,
        padding=px(6),
        width=24,
        height=24,
        sticky="nsew",
    )
    style.layout(
        "Tab.Toolbutton",
        [
            (
                "Tab.rounded",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "Toolbutton.padding",
                            {
                                "sticky": "nsew",
                                "children": [("Toolbutton.label", {"sticky": "nsew"})],
                            },
                        )
                    ],
                },
            )
        ],
    )
    style.configure(
        "Seg.Toolbutton",
        background=BG,
        foreground=MUTED,
        padding=px((12, 3)),
        **_no_3d(),
    )
    style.map(
        "Seg.Toolbutton",
        background=[("selected", ACCENT_SOFT), ("active", BG_SOFT)],
        foreground=[("selected", ACCENT)],
    )

    # Поле ввода тоже со скруглённой рамкой; при фокусе рамка зелёная.
    style.element_create(
        "Rounded.field",
        "image",
        image("field"),
        ("focus", image("field_focus")),
        border=12,
        padding=px(6),
        width=24,
        height=24,
        sticky="nsew",
    )
    style.layout(
        "TEntry",
        [
            (
                "Rounded.field",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "Entry.padding",
                            {
                                "sticky": "nsew",
                                "children": [("Entry.textarea", {"sticky": "nsew"})],
                            },
                        )
                    ],
                },
            )
        ],
    )
    style.configure("TEntry", padding=px((8, 4)))
    style.layout(
        "TCombobox",
        [
            (
                "Rounded.field",
                {
                    "sticky": "nsew",
                    "children": [
                        ("Combobox.downarrow", {"side": "right", "sticky": "ns"}),
                        (
                            "Combobox.padding",
                            {
                                "expand": "1",
                                "sticky": "nsew",
                                "children": [("Combobox.textarea", {"sticky": "nsew"})],
                            },
                        ),
                    ],
                },
            )
        ],
    )
    style.layout(
        "TSpinbox",
        [
            (
                "Rounded.field",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "null",
                            {
                                "side": "right",
                                "sticky": "",
                                "children": [
                                    ("Spinbox.uparrow", {"side": "top", "sticky": "e"}),
                                    (
                                        "Spinbox.downarrow",
                                        {"side": "bottom", "sticky": "e"},
                                    ),
                                ],
                            },
                        ),
                        (
                            "Spinbox.padding",
                            {
                                "sticky": "nsew",
                                "children": [("Spinbox.textarea", {"sticky": "nsew"})],
                            },
                        ),
                    ],
                },
            )
        ],
    )
    flat_box = {"bordercolor": LINE, "lightcolor": BG, "darkcolor": BG}
    style.configure(
        "TCombobox",
        fieldbackground=BG,
        background=BG,
        arrowcolor=MUTED,
        arrowsize=px(13),
        padding=px(4),
        **flat_box,
    )
    style.map("TCombobox", fieldbackground=[("readonly", BG)])
    style.configure(
        "TSpinbox",
        fieldbackground=BG,
        background=BG,
        arrowcolor=MUTED,
        arrowsize=px(13),
        padding=px(4),
        **flat_box,
    )
    style.configure("TCheckbutton", indicatorcolor=BG, indicatorsize=px(15))
    style.configure("Page.TCheckbutton", indicatorsize=px(15))
    style.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)])

    style.configure("Header.TFrame", background=BG)
    style.configure("Page.TFrame", background=PAGE)
    style.configure("Page.TLabel", background=PAGE, foreground=MUTED)
    style.configure("PageInk.TLabel", background=PAGE)
    style.configure("PageBold.TLabel", background=PAGE, font=FONT_BOLD)
    style.configure("Page.TCheckbutton", background=PAGE)
    style.map("Page.TCheckbutton", background=[("active", PAGE)])
    style.configure("Title.TLabel", background=BG)
    style.configure(
        "PageGreen.TLabel", background=PAGE, foreground=ACCENT, font=FONT_BOLD
    )
    style.configure("Line.TFrame", background=LINE)


IMG_DIR = Path(__file__).with_name("img")
_images = {}  # картинки нужно хранить, иначе Tk их удалит


def image(name: str) -> tk.PhotoImage:
    """Загружает картинку из папки ui/img (один раз).

    Args:
        name: Имя файла без расширения .png.

    Returns:
        Картинка Tk.
    """
    if name not in _images:
        _images[name] = tk.PhotoImage(file=str(IMG_DIR / f"{name}.png"))
    return _images[name]


def rounded_button(style, style_name, normal, hover, disabled=None) -> None:
    """Делает кнопку стиля style_name со скруглёнными углами.

    Фон кнопки — картинка со скруглённым прямоугольником. Параметр border=12
    говорит Tk не растягивать углы картинки, а тянуть только середину.

    Args:
        style: Объект ttk.Style.
        style_name: Имя стиля, например «Accent.TButton».
        normal: Картинка обычного состояния.
        hover: Картинка при наведении мыши.
        disabled: Картинка неактивной кнопки (если нужна).
    """
    states = [("active", image(hover))]
    if disabled:
        states.insert(0, ("disabled", image(disabled)))
    element = style_name + ".rounded"
    style.element_create(
        element,
        "image",
        image(normal),
        *states,
        border=12,
        padding=px(6),
        width=24,
        height=24,
        sticky="nsew",
    )
    style.layout(
        style_name,
        [
            (
                element,
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "Button.padding",
                            {
                                "sticky": "nsew",
                                "children": [("Button.label", {"sticky": "nsew"})],
                            },
                        )
                    ],
                },
            )
        ],
    )


def rounded_frame(style, style_name: str, picture: str) -> None:
    """Делает рамку (ttk.Frame) со скруглёнными углами.

    Как и у кнопок, фон рамки — картинка, у которой Tk растягивает только
    середину, а скруглённые углы оставляет как есть.

    Args:
        style: Объект ttk.Style.
        style_name: Имя стиля, например «Card.TFrame».
        picture: Имя картинки из папки img.
    """
    element = style_name + ".rounded"
    style.element_create(
        element,
        "image",
        image(picture),
        border=12,
        padding=px(6),
        width=24,
        height=24,
        sticky="nsew",
    )
    style.layout(style_name, [(element, {"sticky": "nsew"})])


def _no_3d() -> dict:
    """Параметры, убирающие объёмную рамку у кнопок темы clam."""
    return {"bordercolor": LINE, "lightcolor": BG, "darkcolor": BG}


def link(parent, text: str, command, color: str = RED, bg: str = BG) -> tk.Label:
    """Создаёт текстовую ссылку («Выйти», «Зарегистрироваться»).

    Args:
        parent: Родительский виджет.
        text: Текст ссылки.
        command: Функция без аргументов, вызывается по щелчку.
        color: Цвет текста.
        bg: Цвет фона под ссылкой.

    Returns:
        Метка, которая ведёт себя как ссылка.
    """
    label = tk.Label(parent, text=text, fg=color, bg=bg, cursor="hand2", font=FONT)
    label.bind("<Button-1>", lambda event: command())
    return label


def card(parent, title=None, note=None, action=None) -> ttk.Frame:
    """Создаёт белую карточку с тонкой рамкой, как панели в макетах.

    Args:
        parent: Родительский виджет.
        title: Заголовок карточки.
        note: Серая подпись справа от заголовка.
        action: Кнопка справа в заголовке — пара (текст, функция).

    Returns:
        Внутренняя рамка карточки, в неё кладутся поля.
        Саму карточку размещать через .master.
    """
    outer = ttk.Frame(parent, style="Card.TFrame", padding=px(2))
    head_label = None
    if title:
        head = ttk.Frame(outer, padding=px((12, 8)))
        head.pack(fill="x")
        head_label = ttk.Label(head, text=title, style="Bold.TLabel")
        head_label.pack(side="left")
        if note:
            ttk.Label(head, text=note, style="Small.TLabel").pack(side="right")
        if action:
            ttk.Button(
                head, text=action[0], style="Small.TButton", command=action[1]
            ).pack(side="right")
        ttk.Frame(outer, style="Line.TFrame", height=1).pack(fill="x")
    inner = ttk.Frame(outer, padding=px(12))
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
    frame = ttk.Frame(parent, style="Card.TFrame", padding=px(2))
    for index, (text, value) in enumerate(options):
        if index:
            ttk.Frame(frame, style="Line.TFrame", width=1).pack(side="left", fill="y")
        ttk.Radiobutton(
            frame,
            text=text,
            value=value,
            variable=variable,
            command=command,
            style="Seg.Toolbutton",
        ).pack(side="left")
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
        super().__init__(parent, padx=px(12), pady=px(7))
        self.pack_options = pack_options
        self.icon = tk.Label(self, font=FONT_BOLD)
        self.icon.pack(side="left", padx=px((0, 8)))
        self.text = tk.Label(self, justify="left", anchor="w", font=FONT_SMALL)
        self.text.pack(side="left", fill="x", expand=True)
        self.bind(
            "<Configure>", lambda e: self.text.config(wraplength=e.width - px(60))
        )

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

    def __init__(self, parent, columns: int = 1, wrap: int = 0):
        """Создаёт пустой список карточек.

        Args:
            parent: Родительский виджет.
            columns: Сколько карточек в одной строке.
            wrap: Ширина переноса подписи в пикселях (0 — без переноса).
        """
        super().__init__(parent)
        self.columns = columns
        self.wrap = wrap
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
            box = ttk.Frame(self, style="Choice.TFrame", padding=px((10, 6)))
            box.grid(
                row=index // self.columns,
                column=index % self.columns,
                sticky="nsew",
                padx=px((0, 8)) if index % self.columns < self.columns - 1 else 0,
                pady=px((0, 8)),
            )
            mark = tk.Label(box, font=("Segoe UI", 11), bg=BG)
            mark.pack(side="left", padx=px((0, 8)))
            texts = tk.Frame(box, bg=BG)
            texts.pack(side="left", fill="x")
            tk.Label(texts, text=title, font=FONT_BOLD, bg=BG, anchor="w").pack(
                fill="x"
            )
            tk.Label(
                texts,
                text=subtitle,
                fg=MUTED,
                bg=BG,
                anchor="w",
                justify="left",
                font=FONT_SMALL,
                wraplength=px(self.wrap),
            ).pack(fill="x")
            parts = [mark, texts] + list(texts.winfo_children())
            for widget in [box] + parts:
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
            box.config(style="ChoiceOn.TFrame" if chosen else "Choice.TFrame")
            mark.config(text="◉" if chosen else "○", fg=ACCENT if chosen else MUTED)


class MainFrame(ttk.Frame):
    """Окно кабинета, как в образцах: шапка, вкладки, строка итогов внизу."""

    def __init__(self, app, subtitle: str, tabs):
        """Создаёт шапку, вкладки и строку итогов.

        Args:
            app: Приложение (app.user, app.logout, app.show_profile).
            subtitle: Подпись под названием программы.
            tabs: Список пар (название вкладки, класс вкладки).
        """
        super().__init__(app)
        self.app = app
        header = ttk.Frame(self, padding=px((16, 10, 16, 0)))
        header.pack(fill="x")

        brand = ttk.Frame(header)
        brand.pack(side="left", anchor="n", pady=px((0, 8)))
        names = ttk.Frame(brand)
        names.pack(side="left")
        ttk.Label(names, text="Game Master Hub", style="Logo.TLabel").pack(anchor="w")
        ttk.Label(names, text=subtitle, style="Small.TLabel").pack(anchor="w")

        user = ttk.Frame(header)
        user.pack(side="right", anchor="n")
        ttk.Label(user, text=app.user["full_name"], style="Bold.TLabel").pack(
            anchor="e"
        )
        links = ttk.Frame(user)
        links.pack(anchor="e")
        role = "Мастер" if app.user["role"] == "GM" else "Игрок"
        ttk.Label(links, text=role, style="Small.TLabel").pack(side="left")
        for text, command, color in (
            ("Профиль", app.show_profile, ACCENT),
            ("Выйти", app.logout, RED),
        ):
            link(links, text, command, color=color).pack(side="left", padx=px((8, 0)))
            links.winfo_children()[-1].config(font=FONT_SMALL)

        self.current = tk.IntVar(value=0)
        self.tab_buttons = []
        bar = ttk.Frame(header)
        bar.pack(side="left", anchor="s", padx=px((48, 0)))
        ttk.Frame(self, style="Line.TFrame", height=1).pack(fill="x")

        # Строка итогов внизу окна (как в образцах): белая, над ней линия.
        footer = ttk.Frame(self, padding=px((16, 6)))
        footer.pack(side="bottom", fill="x")
        ttk.Frame(self, style="Line.TFrame", height=1).pack(side="bottom", fill="x")
        self.status = ttk.Label(footer, style="Small.TLabel")
        self.status.pack(anchor="w")

        body = ttk.Frame(self, style="Page.TFrame")
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.tabs = []
        for index, (title, tab_class) in enumerate(tabs):
            holder = tk.Frame(bar, bg=BG)
            holder.pack(side="left")
            button = ttk.Radiobutton(
                holder,
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
        # Ctrl+S сохраняет форму на открытой вкладке (если на ней есть форма).
        # Сравниваем код клавиши, чтобы работало и в русской раскладке.
        self.bind_all("<Control-KeyPress>", self.on_ctrl_key)
        self.show_tab()

    def on_ctrl_key(self, event) -> None:
        """Обрабатывает Ctrl+S: вызывает on_save открытой вкладки."""
        if event.keycode == 83:  # клавиша S
            tab = self.tabs[self.current.get()]
            if hasattr(tab, "on_save"):
                tab.on_save()

    def show_tab(self, index: int | None = None) -> None:
        """Показывает вкладку и перечитывает её данные из БД.

        Args:
            index: Номер вкладки. None — текущая выбранная.
        """
        if index is not None:
            self.current.set(index)
        tab = self.tabs[self.current.get()]
        tab.tkraise()
        self.set_status("")
        tab.refresh()
        self.on_tab_shown()

    def on_tab_shown(self) -> None:
        """Вызывается после смены вкладки; переопределяется в окнах."""

    def set_status(self, text: str) -> None:
        """Пишет текст в строку итогов внизу окна.

        Args:
            text: Текст, например «Предстоящих: 4  Свободных мест: 8».
        """
        self.status.config(text=text)


def ask_text(parent, title: str, prompt: str):
    """Небольшое окно с одним полем ввода (например, причина отказа).

    Args:
        parent: Окно, поверх которого открывается диалог.
        title: Заголовок окна.
        prompt: Подпись над полем.

    Returns:
        Введённый текст (может быть пустым) или None, если нажата «Отмена».
    """
    dialog = tk.Toplevel(parent, bg=BG, padx=px(20), pady=px(16))
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent.winfo_toplevel())
    result = {"text": None}
    field(dialog, prompt)
    entry = ttk.Entry(dialog, width=40)
    entry.pack(fill="x")
    entry.focus()

    def done(ok: bool):
        if ok:
            result["text"] = entry.get()
        dialog.destroy()

    buttons = ttk.Frame(dialog)
    buttons.pack(fill="x", pady=px((14, 0)))
    ttk.Button(
        buttons, text="Отклонить", style="Accent.TButton", command=lambda: done(True)
    ).pack(side="right")
    ttk.Button(buttons, text="Отмена", command=lambda: done(False)).pack(
        side="right", padx=px((0, 6))
    )
    entry.bind("<Return>", lambda e: done(True))
    dialog.bind("<Escape>", lambda e: done(False))
    dialog.grab_set()
    parent.wait_window(dialog)
    return result["text"]


def short_name(full_name: str) -> str:
    """Сокращает ФИО для таблицы: «Жукова Полина» -> «Жукова П.».

    Args:
        full_name: Полное имя.

    Returns:
        Фамилия и инициал или имя целиком, если оно из одного слова.
    """
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    return f"{parts[0]} {parts[1][0]}."


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


class RoundText(ttk.Frame):
    """Многострочное поле ввода в скруглённой рамке.

    Attributes:
        text: Само поле Text внутри рамки.
    """

    def __init__(self, parent, height: int = 5, headings: bool = False):
        """Создаёт поле.

        Args:
            parent: Родительский виджет.
            height: Высота в строках.
            headings: Выделять ли жирным заголовки (для заметок).
        """
        self.headings = headings
        super().__init__(parent, style="Card.TFrame", padding=px(3))
        self.text = tk.Text(
            self,
            height=height,
            width=40,
            wrap="word",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=px(8),
            pady=px(5),
            font=FONT,
            bg=BG,
        )
        self.text.pack(fill="both", expand=True)
        # Короткие строки без точки в конце — заголовки («Сцена 1. Обвал»),
        # а «Внешность:» в начале строки — подпись; их выделяем жирным.
        self.text.tag_configure("heading", font=FONT_BOLD)
        self.text.bind("<KeyRelease>", lambda e: self.highlight())

    def highlight(self) -> None:
        """Выделяет жирным заголовки и подписи в тексте заметки."""
        self.text.tag_remove("heading", "1.0", "end")
        if not self.headings:
            return
        lines = self.text.get("1.0", "end-1c").split("\n")
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if len(stripped) <= 60 and stripped[-1] not in ".,!?;:»)":
                self.text.tag_add("heading", f"{number}.0", f"{number}.end")
            elif ":" in stripped[:25]:
                end = line.index(":") + 1
                self.text.tag_add("heading", f"{number}.0", f"{number}.{end}")


def get_text(widget: RoundText) -> str:
    """Возвращает текст многострочного поля без пробелов по краям.

    Args:
        widget: Поле RoundText.

    Returns:
        Текст.
    """
    return widget.text.get("1.0", "end-1c").strip()


def set_text(widget: RoundText, value: str | None) -> None:
    """Заменяет текст многострочного поля.

    Args:
        widget: Поле RoundText.
        value: Новый текст.
    """
    widget.text.delete("1.0", "end")
    widget.text.insert("1.0", value or "")
    widget.highlight()


def make_text(parent, height: int = 5, headings: bool = False) -> RoundText:
    """Создаёт многострочное поле в общем стиле.

    Args:
        parent: Родительский виджет.
        height: Высота в строках.
        headings: Выделять ли жирным заголовки (для заметок).

    Returns:
        Поле RoundText (текст внутри — в атрибуте .text).
    """
    return RoundText(parent, height, headings)


def field(parent, label: str, page: bool = False) -> ttk.Label:
    """Создаёт подпись над полем ввода, как в макетах.

    Args:
        parent: Родительский виджет.
        label: Текст подписи.
        page: Поле лежит на сером фоне страницы, а не в белой карточке.

    Returns:
        Метка (уже размещена через pack).
    """
    style = "PageField.TLabel" if page else "Field.TLabel"
    widget = ttk.Label(parent, text=label, style=style)
    widget.pack(anchor="w", pady=px((7, 2)))
    return widget
