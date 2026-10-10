"""Оформление окон по макетам Figma (п. 4.1.13 ТЗ): шрифты и таблица стилей.

Вид всех кнопок, полей, таблиц и вкладок задаётся одной таблицей стилей
Qt (QSS) — это почти как CSS на веб-страницах. Цвета берутся из выбранной
темы (theme.py), скруглённые углы рисует сам Qt (border-radius).

У виджета можно задать свойство kind, например label.setProperty("kind",
"muted") — тогда он получит оформление из правила QLabel[kind="muted"].
"""

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from gm_hub.settings import read_settings
from gm_hub.ui import theme

# «Крупный текст» (настройка в профиле): шрифты больше на 15 %.
LARGE_TEXT = read_settings().get("large_text") is True

# Размеры как в макетах Figma: основной текст 15 px (11 пт), подписи 13 px.
FONT_FAMILY = "Segoe UI"
TITLE_FAMILY = "Georgia"  # заголовки и логотип


def pt(points: float) -> int:
    """Размер шрифта с учётом настройки «Крупный текст»."""
    return round(points * (1.15 if LARGE_TEXT else 1.0))


def font(points: float = 11, bold: bool = False, title: bool = False) -> QFont:
    """Создаёт шрифт для виджета, который рисуется кодом (числа, имена).

    Args:
        points: Размер в пунктах для обычного текста.
        bold: Жирный ли шрифт.
        title: Шрифт заголовков (Georgia) вместо основного.
    """
    result = QFont(TITLE_FAMILY if title else FONT_FAMILY, pt(points))
    result.setBold(bold)
    return result


def arrow(direction: str) -> str:
    """Рисует маленькую стрелку для списков и счётчиков и сохраняет её в файл.

    Таблица стилей Qt умеет брать картинку только из файла, поэтому стрелка
    рисуется при запуске во временную папку (цвет — из текущей темы).

    Args:
        direction: «up» или «down».

    Returns:
        Путь к картинке со стрелкой (с прямыми косыми чертами для QSS).
    """
    image = QImage(20, 12, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(theme.COLORS["muted"]))
    if direction == "down":
        points = [QPointF(4, 3), QPointF(16, 3), QPointF(10, 10)]
    else:
        points = [QPointF(4, 10), QPointF(16, 10), QPointF(10, 3)]
    painter.drawPolygon(points)
    painter.end()
    path = Path(tempfile.gettempdir()) / f"gm_hub_{direction}_{theme.THEME}.png"
    image.save(str(path))
    return path.as_posix()


def stylesheet() -> str:
    """Собирает таблицу стилей из цветов текущей темы."""
    c = theme.COLORS
    down, up = arrow("down"), arrow("up")
    return f"""
* {{ font-family: "{FONT_FAMILY}"; font-size: {pt(11)}pt; color: {c['ink']}; }}
QMainWindow, QDialog, QScrollArea#main {{ background: {c['bg']}; }}
QFrame#page, QScrollArea#main > QWidget > QWidget {{ background: {c['page']}; }}
QFrame#card {{
    background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 10px;
}}
QFrame#line {{ background: {c['line']}; border: none; }}
QFrame#footer {{ background: {c['bg']}; border-top: 1px solid {c['line']}; }}

QLabel {{ background: transparent; }}
QLabel[kind="muted"] {{ color: {c['muted']}; }}
QLabel[kind="small"] {{ color: {c['muted']}; font-size: {pt(10)}pt; }}
QLabel[kind="caps"] {{ color: {c['muted']}; font-size: {pt(9)}pt; font-weight: 600; }}
QLabel[kind="field"] {{ color: {c['muted']}; font-size: {pt(10)}pt; font-weight: 600; }}
QLabel[kind="page_field"] {{
    color: {c['page_ink']}; font-size: {pt(10)}pt; font-weight: 600;
}}
QLabel[kind="bold"] {{ font-weight: 600; }}
QLabel[kind="page"] {{ color: {c['page_ink']}; }}
QLabel[kind="page_bold"] {{ font-weight: 600; }}
QLabel[kind="green"] {{ color: {c['green_text']}; font-weight: 600; }}
QLabel[kind="title"] {{
    font-family: "{TITLE_FAMILY}"; font-size: {pt(20)}pt; font-weight: bold;
}}
QLabel[kind="heading"] {{
    font-family: "{TITLE_FAMILY}"; font-size: {pt(13)}pt; font-weight: bold;
}}
QLabel[kind="name"] {{
    font-family: "{TITLE_FAMILY}"; font-size: {pt(15)}pt; font-weight: bold;
}}
QLabel[kind="number"] {{
    font-family: "{TITLE_FAMILY}"; font-size: {pt(24)}pt; font-weight: bold;
}}
QLabel[kind="link"] {{ color: {c['red']}; }}
QLabel[kind="link_muted"] {{ color: {c['muted']}; font-size: {pt(10)}pt; }}
QLabel[kind="link_green"] {{ color: {c['green_text']}; font-size: {pt(10)}pt; }}

QFrame#header {{ background: {c['head_bg']}; }}
QLabel[kind="logo"] {{
    color: white; font-family: "{TITLE_FAMILY}"; font-size: {pt(15)}pt;
    font-weight: bold;
}}
QLabel[kind="head_small"] {{ color: {c['head_text']}; font-size: {pt(10)}pt; }}
QLabel[kind="head_bold"] {{ color: white; font-weight: 600; }}
QLabel[kind="head_link"] {{ color: white; font-size: {pt(10)}pt; font-weight: 600; }}
QPushButton[kind="tab"] {{
    background: transparent; color: {c['head_text']}; border: none;
    border-top-left-radius: 10px; border-top-right-radius: 10px;
    padding: 9px 18px; font-weight: 600;
}}
QPushButton[kind="tab"]:hover {{ background: {c['tab_hover']}; color: white; }}
QPushButton[kind="tab"]:checked {{ background: {c['page']}; color: {c['ink']}; }}

QPushButton {{
    background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background: {c['hover_row']}; border-color: {c['check_border']}; }}
QPushButton:disabled {{ color: {c['muted']}; }}
QPushButton[kind="accent"] {{
    background: {c['accent']}; border-color: {c['accent']}; color: white;
    font-weight: 600;
}}
QPushButton[kind="accent"]:hover {{
    background: {c['accent_hover']}; border-color: {c['accent_hover']};
}}
QPushButton[kind="accent"]:disabled {{
    background: {c['accent_disabled']}; border-color: {c['accent_disabled']};
    color: {c['accent_disabled_text']};
}}
QPushButton[kind="danger"] {{ color: {c['red']}; }}
QPushButton[kind="danger"]:hover {{
    background: {c['red_soft']}; border-color: {c['red_line']};
}}
QPushButton[size="small"] {{ padding: 3px 10px; font-size: {pt(10)}pt; }}

QFrame#seg {{
    background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 9px;
}}
QPushButton[kind="seg"] {{
    background: transparent; border: none; border-radius: 7px;
    color: {c['muted']}; padding: 5px 14px;
}}
QPushButton[kind="seg"]:hover {{ background: {c['hover_row']}; }}
QPushButton[kind="seg"]:checked {{
    background: {c['accent_soft']}; color: {c['green_text']};
}}

QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: {c['field']}; border: 1px solid {c['line']}; border-radius: 8px;
    padding: 5px 8px; selection-background-color: {c['accent']};
    selection-color: white;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border-color: {c['accent']};
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{down}"); width: 10px; height: 6px; }}
QSpinBox {{ padding-right: 24px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border; width: 22px; border: none; background: transparent;
}}
QSpinBox::up-button {{ subcontrol-position: top right; margin-top: 3px; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; margin-bottom: 3px; }}
QSpinBox::up-arrow {{ image: url("{up}"); width: 10px; height: 6px; }}
QSpinBox::down-arrow {{ image: url("{down}"); width: 10px; height: 6px; }}
QComboBox QAbstractItemView {{
    background: {c['field']}; border: 1px solid {c['line']};
    selection-background-color: {c['accent']}; selection-color: white;
    outline: none;
}}

QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {c['check_border']}; background: {c['field']};
}}
QCheckBox::indicator:checked {{
    background: {c['accent']}; border-color: {c['accent']};
}}

QTableWidget {{
    background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 10px;
    outline: none;
}}
QTableWidget[flat="true"] {{ border: none; border-radius: 0; }}
QTableWidget::item {{ border-bottom: 1px solid {c['row_line']}; }}
QTableWidget::item:selected {{ background: {c['selected_row']}; color: {c['ink']}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {c['head']}; color: {c['ink']}; font-weight: 600; border: none;
    border-bottom: 1px solid {c['line']}; padding: 7px 8px 7px 16px;
}}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {c['line']}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:hover {{ background: {c['check_border']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QToolTip {{
    background: {c['head_bg']}; color: white; border: none; padding: 4px 8px;
    font-size: {pt(10)}pt;
}}
QMessageBox {{ background: {c['bg']}; }}
QCalendarWidget QWidget {{ alternate-background-color: {c['head']}; }}
QCalendarWidget QToolButton {{
    color: {c['ink']}; background: transparent; font-weight: 600; padding: 4px;
}}
QCalendarWidget QAbstractItemView:enabled {{
    background: {c['bg']}; color: {c['ink']};
    selection-background-color: {c['accent']}; selection-color: white;
}}
QCalendarWidget QAbstractItemView:disabled {{ color: {c['muted']}; }}
QCalendarWidget #qt_calendar_navigationbar {{ background: {c['bg']}; }}
"""


def apply(app) -> None:
    """Применяет шрифт и таблицу стилей ко всей программе.

    Args:
        app: Объект QApplication.
    """
    global LARGE_TEXT
    LARGE_TEXT = read_settings().get("large_text") is True
    app.setFont(font())
    app.setStyleSheet(stylesheet())
