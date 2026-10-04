"""Общие элементы интерфейса: цвета, стили, таблицы (п. 4.1.13 ТЗ)."""

import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timedelta
from tkinter import ttk

from gm_hub.config import DATETIME_FORMAT, SHOW_FORMAT

# Цвета из макетов Figma: винный акцент «обложки книги правил».
ACCENT = "#7b2d3f"
BG = "#f7f8fa"
INK = "#1b1d26"
MUTED = "#5f6475"
ERROR = "#a1362c"

# Подсветка строк таблиц (п. 4.1.6 ТЗ).
ROW_COLORS = {
    "soon": "#f7e9ec",  # сессия скоро, запись истекает
    "PENDING": "#fff1d1",  # новая заявка
    "CONFIRMED": "#e3f3e6",
    "REJECTED": "#fbe7e4",
}

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Georgia", 18, "bold")


def setup_style(root: tk.Tk) -> None:
    """Настраивает единый вид кнопок, таблиц и вкладок.

    Args:
        root: Главное окно.
    """
    root.configure(bg=BG)
    # Меняем стандартные шрифты Tk, а не option_add("*Font"):
    # иначе шрифт из базы опций перебивает шрифты стилей (Title, Bold).
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
        tkfont.nametofont(name).configure(family=FONT[0], size=FONT[1])
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=INK, font=FONT)
    style.configure("TButton", padding=(10, 4))
    style.configure("Accent.TButton", background=ACCENT, foreground="white")
    style.map("Accent.TButton", background=[("active", "#5e2130")])
    style.configure("Treeview", rowheight=26, background="white")
    style.configure("Treeview.Heading", font=FONT_BOLD)
    style.map("Treeview", background=[("selected", ACCENT)])
    style.configure("TNotebook.Tab", padding=(14, 6))
    style.map("TNotebook.Tab", foreground=[("selected", ACCENT)])
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=ACCENT)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Error.TLabel", foreground=ERROR)
    style.configure("Bold.TLabel", font=FONT_BOLD)
    style.configure("Header.TFrame", background=ACCENT)
    style.configure("Header.TLabel", background=ACCENT, foreground="white")


def make_header(parent, app, subtitle: str) -> ttk.Frame:
    """Создаёт верхнюю полосу окна с именем пользователя и кнопкой «Выйти».

    Args:
        parent: Родительский виджет.
        app: Приложение (нужны app.user и app.logout).
        subtitle: Подпись под названием программы.

    Returns:
        Рамка шапки.
    """
    header = ttk.Frame(parent, style="Header.TFrame", padding=(16, 8))
    ttk.Label(
        header, text="Game Master Hub", style="Header.TLabel", font=FONT_TITLE
    ).pack(side="left")
    ttk.Label(header, text="   " + subtitle, style="Header.TLabel").pack(side="left")
    ttk.Button(header, text="Выйти", command=app.logout).pack(side="right")
    ttk.Button(header, text="Профиль", command=app.show_profile).pack(
        side="right", padx=6
    )
    role = "Мастер" if app.user["role"] == "GM" else "Игрок"
    ttk.Label(
        header, text=f"{app.user['full_name']} · {role}   ", style="Header.TLabel"
    ).pack(side="right")
    return header


def _sort_key(text: str):
    """Ключ сортировки: даты по дате, числа по числу, остальное по алфавиту."""
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


def make_table(parent, columns) -> ttk.Treeview:
    """Создаёт таблицу с прокруткой и сортировкой по столбцам.

    Args:
        parent: Родительский виджет.
        columns: Список пар (заголовок, ширина).

    Returns:
        Таблица Treeview. Рамку с ней нужно разместить через tree.master.
    """
    frame = ttk.Frame(parent)
    ids = [f"c{i}" for i in range(len(columns))]
    tree = ttk.Treeview(frame, columns=ids, show="headings", selectmode="browse")
    for col_id, (title, width) in zip(ids, columns):
        tree.heading(col_id, text=title, command=lambda c=col_id: sort_table(tree, c))
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
        relief="solid",
        bd=1,
        padx=6,
        font=FONT,
    )
