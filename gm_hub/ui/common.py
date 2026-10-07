"""Общие элементы интерфейса по макетам Figma (п. 4.1.13 ТЗ).

Здесь цвета, стили ttk, шапка окна со вкладками, таблицы, баннеры
и карточки выбора — всё, что повторяется в нескольких окнах.
"""

import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

from gm_hub.config import DATETIME_FORMAT
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.theme import COLORS as C
from gm_hub.ui.theme import THEME

# Цвета берутся из выбранной темы (светлая или тёмная, см. theme.py).
ACCENT = C["accent"]  # кнопки
ACCENT_HOVER = C["accent_hover"]
ACCENT_SOFT = C["accent_soft"]  # выбранный фильтр
ACCENT_DISABLED_TEXT = C["accent_disabled_text"]
GREEN_SOFT = C["green_soft"]  # успех, выбранная карточка
GREEN_TEXT = C["green_text"]
BG = C["bg"]  # карточки и таблицы
FIELD = C["field"]  # поля ввода
PAGE = C["page"]  # фон страницы под карточками
PAGE_INK = C["page_ink"]  # подписи прямо на фоне страницы
HEAD_BG = C["head_bg"]  # шапка окна
HEAD_TEXT = C["head_text"]  # подписи в шапке
HEAD = C["head"]  # заголовки таблиц
LINE = C["line"]
INK = C["ink"]
MUTED = C["muted"]
RED = C["red"]
RED_SOFT = C["red_soft"]
YELLOW = C["yellow"]
YELLOW_SOFT = C["yellow_soft"]

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
        "PageField.TLabel", background=PAGE, foreground=PAGE_INK, font=FONT_SMALL_BOLD
    )
    style.configure("Caps.TLabel", foreground=MUTED, font=FONT_SMALL_BOLD)
    style.configure("Bold.TLabel", font=FONT_BOLD)
    style.configure("Title.TLabel", font=FONT_TITLE)
    style.configure("Logo.TLabel", font=FONT_LOGO)
    style.configure("Green.TLabel", foreground=GREEN_TEXT, font=FONT_BOLD)

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
    style.map("Accent.TButton", foreground=[("disabled", ACCENT_DISABLED_TEXT)])
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
    # Полосы прокрутки окна в цветах темы (появляются, если окно уменьшить).
    style.configure(
        "TScrollbar",
        background=HEAD,
        troughcolor=PAGE,
        bordercolor=PAGE,
        lightcolor=HEAD,
        darkcolor=HEAD,
        arrowcolor=MUTED,
        gripcount=0,
    )
    style.map("TScrollbar", background=[("active", LINE)])
    style.configure(
        "Small.Accent.TButton", foreground="white", font=FONT_SMALL, padding=px((9, 2))
    )
    style.map("Small.Accent.TButton", foreground=[("disabled", ACCENT_DISABLED_TEXT)])
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
    style.configure("Tab.Toolbutton", foreground=HEAD_TEXT, background=HEAD_BG)
    style.map(
        "Tab.Toolbutton",
        foreground=[("selected", INK), ("active", "white")],
        # уголки картинки-закладки заливаются цветом шапки — тогда они круглые
        background=[("selected", HEAD_BG), ("active", HEAD_BG)],
    )
    style.configure("Head.TFrame", background=HEAD_BG)
    style.configure(
        "HeadLogo.TLabel", background=HEAD_BG, foreground="white", font=FONT_LOGO
    )
    style.configure(
        "HeadSmall.TLabel", background=HEAD_BG, foreground=HEAD_TEXT, font=FONT_SMALL
    )
    style.configure(
        "HeadBold.TLabel", background=HEAD_BG, foreground="white", font=FONT_BOLD
    )
    # Выбранная вкладка — закладка со скруглёнными верхними углами.
    style.element_create(
        "Tab.rounded",
        "image",
        image("tab_off"),
        ("selected", image("tab_on")),
        ("active", image("tab_hover")),
        border=18,
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
        foreground=[("selected", GREEN_TEXT)],
        background=[(state, BG) for state in ("disabled", "pressed", "active")],
    )
    image_layout(
        style,
        "Seg.Toolbutton",
        "seg_off",
        [("selected", "seg_on"), ("active", "seg_hover")],
        "Toolbutton",
    )
    # Плашки сообщений — тоже со скруглёнными углами.
    rounded_frame(style, "BannerError.TFrame", "banner_error")
    rounded_frame(style, "BannerOk.TFrame", "banner_ok")
    rounded_frame(style, "TableHead.TFrame", "table_head")  # заголовок таблицы

    # Поле ввода тоже со скруглённой рамкой; при фокусе рамка зелёная.
    style.element_create(
        "Rounded.field",
        "image",
        image("field"),
        ("focus", image("field_focus")),
        border=18,
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
    style.configure(
        "TEntry", padding=px((8, 4)), fieldbackground=FIELD, insertcolor=INK
    )
    # выпадающий список Combobox — обычный Listbox, его цвета задаются отдельно
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", INK)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
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
    # Рамку поля рисует скруглённая картинка, у кнопки-стрелки рамки нет.
    flat_box = {"bordercolor": BG, "lightcolor": BG, "darkcolor": BG}
    style.configure(
        "TCombobox",
        fieldbackground=FIELD,
        foreground=INK,
        insertcolor=INK,
        background=BG,
        arrowcolor=MUTED,
        arrowsize=px(13),
        padding=px(4),
        **flat_box,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", FIELD)],
        foreground=[("readonly", INK)],
        selectbackground=[("readonly", FIELD)],
        selectforeground=[("readonly", INK)],
    )
    style.configure(
        "TSpinbox",
        fieldbackground=FIELD,
        foreground=INK,
        insertcolor=INK,
        background=BG,
        arrowcolor=MUTED,
        arrowsize=px(13),
        padding=px(4),
        **flat_box,
    )
    # Галочка — картинка со скруглёнными углами.
    style.element_create(
        "Rounded.check", "image", image("check_off"), ("selected", image("check_on"))
    )
    for name in ("TCheckbutton", "Page.TCheckbutton"):
        style.layout(
            name,
            [
                (
                    "Checkbutton.padding",
                    {
                        "sticky": "nsew",
                        "children": [
                            ("Rounded.check", {"side": "left", "sticky": ""}),
                            ("Checkbutton.label", {"side": "left", "sticky": "nsew"}),
                        ],
                    },
                )
            ],
        )
    style.configure("TCheckbutton", padding=px((0, 2)))
    style.map("TCheckbutton", indicatorcolor=[("selected", ACCENT)])

    style.configure("Header.TFrame", background=BG)
    style.configure("Page.TFrame", background=PAGE)
    style.configure("Page.TLabel", background=PAGE, foreground=PAGE_INK)
    style.configure("PageInk.TLabel", background=PAGE)
    style.configure("PageBold.TLabel", background=PAGE, font=FONT_BOLD)
    style.configure("Page.TCheckbutton", background=PAGE)
    style.map("Page.TCheckbutton", background=[("active", PAGE)])
    style.configure("Title.TLabel", background=BG)
    style.configure(
        "PageGreen.TLabel", background=PAGE, foreground=GREEN_TEXT, font=FONT_BOLD
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
        folder = IMG_DIR / "dark" if THEME == "dark" else IMG_DIR
        _images[name] = tk.PhotoImage(file=str(folder / f"{name}.png"))
    return _images[name]


def keep_background(style, style_name: str, color: str) -> None:
    """Не даёт теме clam менять фон кнопки при наведении и нажатии.

    clam при наведении делает фон светлым, а у скруглённой картинки этот
    фон виден в уголках — в тёмной теме получались светлые точки по углам.

    Args:
        style: Объект ttk.Style.
        style_name: Имя стиля.
        color: Фон, который нужен во всех состояниях.
    """
    style.map(
        style_name,
        background=[(state, color) for state in ("disabled", "pressed", "active")],
    )


def rounded_button(style, style_name, normal, hover, disabled=None) -> None:
    """Делает кнопку стиля style_name со скруглёнными углами.

    Фон кнопки — картинка со скруглённым прямоугольником. Параметр border=18
    говорит Tk не растягивать углы картинки, а тянуть только середину.

    Args:
        style: Объект ttk.Style.
        style_name: Имя стиля, например «Accent.TButton».
        normal: Картинка обычного состояния.
        hover: Картинка при наведении мыши.
        disabled: Картинка неактивной кнопки (если нужна).
    """
    keep_background(style, style_name, BG)
    states = [("active", image(hover))]
    if disabled:
        states.insert(0, ("disabled", image(disabled)))
    element = style_name + ".rounded"
    style.element_create(
        element,
        "image",
        image(normal),
        *states,
        border=18,
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


def image_layout(style, style_name, normal, states, base) -> None:
    """Делает фон кнопки-переключателя скруглённой картинкой.

    Args:
        style: Объект ttk.Style.
        style_name: Имя стиля, например «Seg.Toolbutton».
        normal: Картинка обычного состояния.
        states: Список пар (состояние, картинка), например («selected», …).
        base: Базовый класс элементов, например «Toolbutton».
    """
    element = style_name + ".rounded"
    style.element_create(
        element,
        "image",
        image(normal),
        *[(state, image(name)) for state, name in states],
        border=18,
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
                            base + ".padding",
                            {
                                "sticky": "nsew",
                                "children": [(base + ".label", {"sticky": "nsew"})],
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
        border=18,
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
    outer = ttk.Frame(parent, style="Card.TFrame", padding=px(5))
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
        ttk.Radiobutton(
            frame,
            text=text,
            value=value,
            variable=variable,
            command=command,
            style="Seg.Toolbutton",
        ).pack(side="left")
    return frame


class Banner(ttk.Frame):
    """Цветная плашка с сообщением: ошибка (красная) или успех (зелёная)."""

    KINDS = {
        "error": ("!", RED_SOFT, RED, "BannerError.TFrame"),
        "ok": ("✓", GREEN_SOFT, ACCENT, "BannerOk.TFrame"),
    }

    def __init__(self, parent, **pack_options):
        """Создаёт скрытую плашку.

        Args:
            parent: Родительский виджет.
            **pack_options: Как размещать плашку при показе (параметры pack).
        """
        super().__init__(parent, style="BannerError.TFrame", padding=px((14, 9)))
        self.pack_options = pack_options
        self.prefix = "Page." if on_page(self) else ""  # фон уголков плашки
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
        icon, bg, fg, style = self.KINDS[kind]
        if self.prefix:
            ttk.Style(self).configure(self.prefix + style, background=PAGE)
        self.config(style=self.prefix + style)
        for widget in (self.icon, self.text):
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
            tk.Label(texts, text=title, font=FONT_BOLD, bg=BG, fg=INK, anchor="w").pack(
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
        super().__init__(app.scroll.page)
        self.app = app
        header = ttk.Frame(self, padding=px((16, 10, 16, 0)), style="Head.TFrame")
        header.pack(fill="x")

        brand = ttk.Frame(header, style="Head.TFrame")
        brand.pack(side="left", anchor="n", pady=px((0, 10)))
        ttk.Label(brand, text="Game Master Hub", style="HeadLogo.TLabel").pack(
            anchor="w"
        )
        ttk.Label(brand, text=subtitle, style="HeadSmall.TLabel").pack(anchor="w")

        user = ttk.Frame(header, style="Head.TFrame")
        user.pack(side="right", anchor="n")
        ttk.Label(user, text=app.user["full_name"], style="HeadBold.TLabel").pack(
            anchor="e"
        )
        links = ttk.Frame(user, style="Head.TFrame")
        links.pack(anchor="e")
        role = "Мастер" if app.user["role"] == "GM" else "Игрок"
        ttk.Label(links, text=role, style="HeadSmall.TLabel").pack(side="left")
        theme_text = "Светлая тема" if THEME == "dark" else "Тёмная тема"
        for text, command in (
            (theme_text, app.toggle_theme),
            ("Профиль", app.show_profile),
            ("Выйти", app.logout),
        ):
            label = link(links, text, command, color="white", bg=HEAD_BG)
            label.config(font=FONT_SMALL_BOLD)
            label.pack(side="left", padx=px((10, 0)))

        self.current = tk.IntVar(value=0)
        self.shown = None  # номер вкладки, которая сейчас на экране
        self.tab_buttons = []
        self.tab_titles = [title for title, _ in tabs]
        bar = ttk.Frame(header, style="Head.TFrame")
        bar.pack(side="left", anchor="s", padx=px((48, 0)))

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
            holder = tk.Frame(bar, bg=HEAD_BG)
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
        fix_corners(self)
        self.show_tab()
        self.poll_id = None
        self.poll_badges()

    def update_badges(self) -> None:
        """Обновляет числа на вкладках; переопределяется в окнах."""

    def poll_badges(self) -> None:
        """Раз в 30 секунд обновляет числа на вкладках (новые заявки, решения)."""
        self.update_badges()
        self.poll_id = self.after(30000, self.poll_badges)

    def destroy(self) -> None:
        """Останавливает обновление вкладок и закрывает окно кабинета."""
        if self.poll_id is not None:
            self.after_cancel(self.poll_id)
        super().destroy()

    def on_ctrl_key(self, event) -> None:
        """Обрабатывает Ctrl+S: вызывает on_save открытой вкладки."""
        if event.keycode == 83:  # клавиша S
            tab = self.tabs[self.current.get()]
            if hasattr(tab, "on_save"):
                tab.on_save()

    def show_tab(self, index: int | None = None) -> None:
        """Показывает вкладку и перечитывает её данные из БД.

        Если на открытой вкладке есть несохранённые изменения, сначала
        спрашивает, сохранить ли их; при «Отмене» вкладка не меняется.

        Args:
            index: Номер вкладки. None — текущая выбранная.
        """
        if index is not None:
            self.current.set(index)
        new = self.current.get()
        if self.shown is not None and new != self.shown:
            if not self.tabs[self.shown].can_leave():
                self.current.set(self.shown)
                return
        self.shown = new
        tab = self.tabs[new]
        tab.tkraise()
        self.set_status("")
        tab.refresh()
        self.on_tab_shown()

    def can_leave(self) -> bool:
        """Проверяет несохранённые изменения на открытой вкладке.

        Returns:
            True, если можно уйти с вкладки (выйти, сменить тему).
        """
        return self.shown is None or self.tabs[self.shown].can_leave()

    def set_badge(self, index: int, count: int) -> None:
        """Показывает число рядом с названием вкладки: «Мои записи (2)».

        Args:
            index: Номер вкладки.
            count: Число; 0 — убрать отметку.
        """
        title = self.tab_titles[index]
        self.tab_buttons[index].config(text=f"{title} ({count})" if count else title)

    def on_tab_shown(self) -> None:
        """Вызывается после смены вкладки: обновляет числа на вкладках."""
        self.update_badges()

    def set_status(self, text: str) -> None:
        """Пишет текст в строку итогов внизу окна.

        Args:
            text: Текст, например «Предстоящих: 4  Свободных мест: 8».
        """
        self.status.config(text=text)


class ScrollArea(ttk.Frame):
    """Область окна с ползунками.

    Пока окно не меньше нужного размера, экран растягивается на всё окно и
    ползунков не видно. Если окно уменьшить, экран сохраняет свой размер, а
    справа и снизу появляются полосы прокрутки.

    Attributes:
        page: Рамка, в которую помещается экран (вход, кабинет и т. д.).
    """

    def __init__(self, parent):
        """Создаёт холст с ползунками.

        Args:
            parent: Главное окно.
        """
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=PAGE, highlightthickness=0, bd=0)
        self.v_bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_bar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(
            yscrollcommand=self.v_bar.set, xscrollcommand=self.h_bar.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.page = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.page, anchor="nw")
        self.min_width = self.min_height = 0
        self.canvas.bind("<Configure>", self.resize)
        # Колесо мыши занято таблицами, поэтому окно прокручивается с Shift.
        self.bind_all("<Shift-MouseWheel>", self.on_wheel)

    def on_wheel(self, event) -> None:
        """Shift + колесо: прокрутка окна вверх-вниз (или влево-вправо)."""
        step = -event.delta // 120
        if self.v_bar.winfo_ismapped():
            self.canvas.yview_scroll(step, "units")
        elif self.h_bar.winfo_ismapped():
            self.canvas.xview_scroll(step, "units")

    def set_min_size(self, width: int, height: int) -> None:
        """Задаёт размер, меньше которого экран не сжимается.

        Args:
            width: Ширина в пикселях.
            height: Высота в пикселях.
        """
        self.min_width, self.min_height = width, height
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.resize()

    def resize(self, _event=None) -> None:
        """Подгоняет экран под окно и показывает ползунки, если они нужны."""
        view_width = self.canvas.winfo_width()
        view_height = self.canvas.winfo_height()
        width = max(view_width, self.min_width)
        height = max(view_height, self.min_height)
        self.canvas.itemconfigure(self.window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        if width > view_width:
            self.h_bar.grid(row=1, column=0, sticky="ew")
        else:
            self.h_bar.grid_remove()
        if height > view_height:
            self.v_bar.grid(row=0, column=1, sticky="ns")
        else:
            self.v_bar.grid_remove()


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
        answer = messagebox.askyesnocancel(
            "Несохранённые изменения", "Сохранить изменения?", parent=self
        )
        if answer is None:
            return False
        if answer:
            try:
                self.on_save()
            except ValidationError as error:
                messagebox.showwarning("Проверьте данные", error.message, parent=self)
                return False
            return not self.is_dirty()
        self.discard()
        return True


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


# Стили со скруглёнными картинками. Прозрачные уголки картинки Tk заливает
# фоном самого виджета, поэтому на мятном фоне страницы им нужен мятный фон.
ROUNDED_STYLES = {
    "TButton",
    "Accent.TButton",
    "Danger.TButton",
    "Small.TButton",
    "TEntry",
    "TCombobox",
    "TSpinbox",
    "Card.TFrame",
}


def on_page(widget) -> bool:
    """Проверяет, лежит ли виджет прямо на мятном фоне страницы."""
    parent = widget.master
    if isinstance(parent, ttk.Widget):
        return "Page" in str(parent.cget("style"))
    return str(parent.cget("bg")).lower() == PAGE


def fix_corners(widget) -> None:
    """Делает уголки скруглённых элементов на фоне страницы мятными.

    Для элемента на странице создаётся стиль «Page.<стиль>» — он берёт всё
    оформление исходного стиля, меняется только цвет фона.

    Args:
        widget: Окно или рамка, внутри которой проверить все элементы.
    """
    for child in widget.winfo_children():
        if isinstance(child, ttk.Widget):
            name = str(child.cget("style")) or child.winfo_class()
            if name in ROUNDED_STYLES and on_page(child):
                page_style = "Page." + name
                style = ttk.Style(child)
                style.configure(page_style, background=PAGE)
                keep_background(style, page_style, PAGE)
                child.configure(style=page_style)
        fix_corners(child)


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
        super().__init__(parent, style="Card.TFrame", padding=px(5))
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
            bg=FIELD,
            fg=INK,
            insertbackground=INK,
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
        page: Поле лежит на зелёном фоне страницы, а не в белой карточке.

    Returns:
        Метка (уже размещена через pack).
    """
    style = "PageField.TLabel" if page else "Field.TLabel"
    widget = ttk.Label(parent, text=label, style=style)
    widget.pack(anchor="w", pady=px((7, 2)))
    return widget
