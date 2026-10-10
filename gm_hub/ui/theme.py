"""Светлая и тёмная темы оформления.

Выбранная тема хранится в файле settings.json рядом с БД и читается при
запуске. Окна берут цвета через функцию c(), поэтому после смены темы
новые окна сразу рисуются в новых цветах.
"""

from gm_hub.settings import SETTINGS_PATH, read_settings, write_setting

LIGHT = {
    "accent": "#285331",  # тёмно-зелёные кнопки
    "accent_hover": "#1e4026",
    "accent_soft": "#c3cfc6",  # выбранный фильтр
    "accent_disabled": "#e3eee5",
    "accent_disabled_text": "#8fa596",
    "green_soft": "#e3f3e6",  # успех, выбранная карточка
    "green_text": "#2a7a3b",
    "green_line": "#cfe6d4",
    "bg": "#ffffff",  # карточки и таблицы
    "field": "#ffffff",  # поля ввода
    "page": "#d9eedd",  # фон страницы — мятный зелёный
    "page_ink": "#3d5a44",  # подписи прямо на фоне страницы
    "head_bg": "#285331",  # шапка окна
    "head_text": "#d4e7d8",
    "tab_hover": "#3a6d45",
    "head": "#eef0f4",  # заголовки таблиц
    "line": "#d6d9e2",
    "ink": "#1b1d26",  # основной текст
    "muted": "#5f6475",  # серый текст
    "seat_taken": "#285331",
    "seat_free": "#9aa1b0",
    "red": "#a1362c",
    "red_soft": "#fbe7e4",
    "red_line": "#efc9c4",
    "yellow": "#8a5a00",
    "yellow_soft": "#fff1d1",
    "row_line": "#e7e9ef",
    "pending_row": "#fff6e3",
    "soon_row": "#eef5ef",
    "selected_row": "#e1f0e4",
    "hover_row": "#f3f8f4",
    "check_border": "#9aa7a0",
}

DARK = {
    "accent": "#3f8f55",
    "accent_hover": "#347546",  # при наведении темнее, как в светлой теме
    "accent_soft": "#2e5a3c",
    "accent_disabled": "#26372d",
    "accent_disabled_text": "#6f8a77",
    "green_soft": "#1f3a29",
    "green_text": "#7fd08f",
    "green_line": "#2f5a3d",
    "bg": "#1c2822",
    "field": "#141e19",
    "page": "#111a15",
    "page_ink": "#9fbca9",
    "head_bg": "#0b130f",
    "head_text": "#a9c7b3",
    "tab_hover": "#1f3328",
    "head": "#24332b",
    "line": "#33463b",
    "ink": "#e4eee7",
    "muted": "#97ad9f",
    "seat_taken": "#5fbf7a",
    "seat_free": "#5d7266",
    "red": "#f0938a",
    "red_soft": "#3b211e",
    "red_line": "#5a2f2a",
    "yellow": "#f0b95a",
    "yellow_soft": "#3a2e15",
    "row_line": "#2a3a31",
    "pending_row": "#2d2716",
    "soon_row": "#1c3024",
    "selected_row": "#24402e",
    "hover_row": "#22302a",
    "check_border": "#5d7266",
}


def load_theme(path=SETTINGS_PATH) -> str:
    """Читает выбранную тему из файла настроек.

    Args:
        path: Путь к settings.json.

    Returns:
        «light» или «dark» (если файла нет или он испорчен — «light»).
    """
    return "dark" if read_settings(path).get("theme") == "dark" else "light"


def save_theme(theme: str, path=SETTINGS_PATH) -> None:
    """Сохраняет выбранную тему (запомненные логины в файле остаются).

    Args:
        theme: «light» или «dark».
        path: Путь к settings.json.
    """
    write_setting("theme", theme, path)


THEME = load_theme()
COLORS = DARK if THEME == "dark" else LIGHT


def set_theme(theme: str) -> None:
    """Включает тему в работающей программе (без сохранения в файл).

    Args:
        theme: «light» или «dark».
    """
    global THEME, COLORS
    THEME = theme
    COLORS = DARK if theme == "dark" else LIGHT


def c(name: str) -> str:
    """Возвращает цвет текущей темы по имени, например c("accent")."""
    return COLORS[name]
