"""Окно Мастера: «Расписание», «Заявки», «Сюжетный блокнот», «База мира»,
«Статистика» и «Календарь».

Макеты 03–06. У каждого Мастера своё окно: здесь видны только его сессии,
заявки на них, его заметки и его база мира.
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from gm_hub.config import to_short, to_show
from gm_hub.logic import characters, dice, games, month, notes, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    Banner,
    Card,
    ClickLabel,
    DatePicker,
    FormGuard,
    MainFrame,
    Pill,
    SeatsBar,
    Segmented,
    Tab,
    ask,
    ask_text,
    button,
    clear_layout,
    field,
    get_text,
    hbox,
    hline,
    info,
    is_soon,
    label,
    link,
    make_text,
    set_text,
    short_name,
    vbox,
)
from gm_hub.ui.mask import DATE_MASK, TIME_MASK, MaskedEntry
from gm_hub.ui.table import STATUS_PILL, RowTable
from gm_hub.ui.theme import c


def free_of(game) -> int:
    """Возвращает число свободных мест сессии по формуле F = M − C."""
    return games.free_seats(game["max_players"], game["confirmed"])


class GMFrame(MainFrame):
    """Главное окно Мастера с вкладками."""

    def __init__(self, app):
        """Создаёт шапку и вкладки.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(
            app,
            "Кабинет Мастера",
            [
                ("Расписание", ScheduleTab),
                ("Заявки", SignupsTab),
                ("Сюжетный блокнот", GameNotesTab),
                ("База мира", WorldTab),
                ("Статистика", StatsTab),
                ("Календарь", CalendarTab),
            ],
        )

    def update_badges(self) -> None:
        """Пишет на вкладке «Заявки» число заявок, ждущих решения."""
        planned = games.list_games(self.app.conn, "PLANNED", self.app.user["id"])
        self.set_badge(1, sum(game["pending"] for game in planned))


class GMTab(Tab):
    """Вкладка Мастера: доступ к его сессиям."""

    def my_games(self, status: str = "PLANNED"):
        """Возвращает сессии текущего Мастера с нужным статусом."""
        return games.list_games(self.app.conn, status, self.app.user["id"])


class ScheduleTab(FormGuard, GMTab):
    """Вкладка «Расписание»: список сессий и форма сессии (макет 03)."""

    PERIODS = [
        ("Предстоящие", "PLANNED"),
        ("Прошедшие", "CLOSED"),
        ("Отменённые", "CANCELLED"),
    ]

    def __init__(self, main, app):
        """Создаёт таблицу сессий и форму.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app, "h")
        self.game_id = None  # id сессии в форме, None — новая сессия

        left = vbox(spacing=12)
        self.box.addLayout(left, 1)
        top = hbox(spacing=6)
        left.addLayout(top)
        self.period = Segmented(self.PERIODS, "PLANNED", self.refresh)
        top.addWidget(self.period)
        top.addStretch()
        top.addWidget(button("+ Новая сессия", self.on_new, "accent"))
        top.addWidget(button("Отменить сессию", self.on_cancel, "danger"))
        # «Удалить» видна только на вкладке «Отменённые» (см. refresh)
        self.delete_button = button("Удалить", self.on_delete, "danger")
        top.addWidget(self.delete_button)

        self.table = RowTable(
            [
                ("Название", 320, True),
                ("Дата и время", 150, False),
                ("Места", 160, False),
                ("Новых заявок", 120, False),
                ("Статус", 140, False),
            ],
            on_select=self.on_select,
        )
        left.addWidget(self.table, 1)

        self.form = Card("Новая сессия")
        self.form.setFixedWidth(360)
        self.box.addWidget(self.form)
        form = self.form.body
        field(form, "Название *")
        self.title_entry = QLineEdit()
        form.addWidget(self.title_entry)
        field(form, "Описание для игроков")
        self.description = make_text(height=3)
        form.addWidget(self.description)
        row = hbox(spacing=8)
        date_box, time_box = vbox(spacing=2), vbox(spacing=2)
        row.addLayout(date_box, 3)
        row.addLayout(time_box, 2)
        # вводятся только цифры, точки и двоеточие ставятся сами
        date_head = hbox(margins=(0, 8, 0, 2))
        date_head.addWidget(label("Дата * (ДД.ММ.ГГГГ)", "field"))
        date_head.addStretch()
        date_head.addWidget(
            link("календарь", lambda: DatePicker(self.date_entry), "link_green")
        )
        date_box.addLayout(date_head)
        self.date_entry = MaskedEntry(DATE_MASK)
        date_box.addWidget(self.date_entry)
        field(time_box, "Время * (ЧЧ:ММ)")
        self.time_entry = MaskedEntry(TIME_MASK)
        time_box.addWidget(self.time_entry)
        form.addLayout(row)
        field(form, "Лимит мест *")
        self.max_players = QSpinBox()
        self.max_players.setRange(1, 50)
        self.max_players.setFixedWidth(110)
        form.addWidget(self.max_players)
        form.addWidget(label("Целое число больше нуля", "small"))
        form.addSpacing(12)
        self.error = Banner()
        form.addWidget(self.error)
        form.addSpacing(4)
        self.save_button = button("Опубликовать", self.on_save, "accent")
        form.addWidget(self.save_button)
        form.addStretch()
        # Enter в полях формы — «Опубликовать»/«Сохранить», Esc — новая сессия.
        for entry in (self.title_entry, self.date_entry, self.time_entry):
            entry.returnPressed.connect(self.on_save)
        escape = QShortcut(QKeySequence("Esc"), self.form)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(self.on_new)
        self.clear_form()

    def form_state(self):
        """Значения полей формы — чтобы заметить несохранённые правки."""
        return (
            self.title_entry.text(),
            get_text(self.description),
            self.date_entry.text(),
            self.time_entry.text(),
            self.max_players.value(),
        )

    def discard(self):
        """Отбрасывает правки: возвращает сохранённую сессию в форму."""
        if self.game_id is None:
            self.clear_form()
        else:
            self.load_game(self.game_id)

    def on_new(self):
        """Кнопка «+ Новая сессия» и Esc: пустая форма (с вопросом о правках)."""
        if self.can_leave():
            self.clear_form()

    def refresh(self):
        """Перечитывает сессии текущего Мастера из БД."""
        period = self.period.value()
        self.delete_button.setVisible(period == "CANCELLED")
        hints = {
            "PLANNED": "Предстоящих сессий пока нет.\n"
            "Нажмите «+ Новая сессия», чтобы опубликовать первую игру.",
            "CLOSED": "Прошедших сессий пока нет.",
            "CANCELLED": "Отменённых сессий нет.",
        }
        self.table.clear(hints[period])
        for game in self.my_games(period):
            free = free_of(game)
            title = [("bold", game["title"])]
            if game["description"]:
                title.append(("muted", game["description"]))
            self.table.add(
                game["id"],
                [
                    ("stack", title),
                    to_show(game["scheduled_at"]),
                    ("seats", game["confirmed"], free),
                    game["pending"],
                    (
                        "pill",
                        games.STATUS_NAMES[game["status"]],
                        STATUS_PILL[game["status"]],
                    ),
                ],
                sort=[
                    game["title"].lower(),
                    game["scheduled_at"],
                    free,
                    game["pending"],
                    game["status"],
                ],
                highlight="soon" if is_soon(game["scheduled_at"]) else False,
            )
        if self.game_id in self.table.rows:
            self.table.select(self.game_id, notify=False)
        planned = self.my_games()
        free = sum(free_of(game) for game in planned)
        pending = sum(game["pending"] for game in planned)
        self.status(
            f"Предстоящих: {len(planned)}      Свободных мест всего: {free}      "
            f"Заявок ждут решения: {pending}"
        )

    def clear_form(self):
        """Очищает форму для новой сессии."""
        self.game_id = None
        self.form.title_label.setText("Новая сессия")
        self.save_button.setText("Опубликовать")
        self.title_entry.clear()
        set_text(self.description, "")
        self.date_entry.clear()
        self.time_entry.clear()
        self.max_players.setValue(4)
        self.error.hide()
        self.refresh()
        self.remember()

    def on_select(self, game_id):
        """Загружает выбранную сессию в форму (спросив о несохранённых правках)."""
        if game_id != self.game_id and not self.can_leave():
            self.table.select(self.game_id, notify=False)
            return
        self.load_game(game_id)

    def load_game(self, game_id):
        """Загружает сессию в форму для изменения."""
        game = games.get_game(self.app.conn, game_id)
        self.game_id = game_id
        self.form.title_label.setText("Изменение сессии")
        self.save_button.setText("Сохранить")
        self.title_entry.setText(game["title"])
        set_text(self.description, game["description"])
        when = to_show(game["scheduled_at"])
        self.date_entry.setText(when[:10])
        self.time_entry.setText(when[11:])
        self.max_players.setValue(game["max_players"])
        self.error.hide()
        self.table.select(game_id, notify=False)
        self.remember()

    def on_save(self):
        """Сохраняет сессию из формы; ошибку показывает в форме."""
        try:
            games.save_game(
                self.app.conn,
                self.app.user,
                self.title_entry.text(),
                get_text(self.description),
                self.date_entry.text(),
                self.time_entry.text(),
                str(self.max_players.value()),
                self.game_id,
            )
        except ValidationError as error:
            self.error.show_message(error.message)
            return
        self.clear_form()

    def selected_game(self) -> int:
        """Возвращает id выбранной сессии или сообщает, что её нет."""
        if self.table.selected is None:
            raise ValidationError("Сессия", "Выберите сессию в таблице.")
        return self.table.selected

    def on_cancel(self):
        """Отменяет выбранную сессию после подтверждения."""
        game_id = self.selected_game()
        if ask(self, "Отмена сессии", "Отменить выбранную сессию?"):
            games.cancel_game(self.app.conn, self.app.user, game_id)
            self.clear_form()

    def on_delete(self):
        """Удаляет выбранную отменённую сессию после подтверждения."""
        if self.period.value() != "CANCELLED":
            return  # удалять можно только на вкладке «Отменённые»
        game_id = self.selected_game()
        question = "Удалить сессию вместе с заявками и заметкой?"
        if ask(self, "Удаление сессии", question):
            games.delete_game(self.app.conn, self.app.user, game_id)
            self.clear_form()


class SignupsTab(GMTab):
    """Вкладка «Заявки»: подтверждение и отклонение (макет 04)."""

    STATUS_FILTER = ["Все статусы"] + list(signups.STATUS_NAMES.values())

    def __init__(self, main, app):
        """Создаёт выбор сессии, таблицу заявок и карточку персонажа.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app, "h")
        self.game_ids = {}  # подпись в списке -> id сессии
        self.rows = {}  # id заявки -> строка заявки

        left = vbox(spacing=12)
        self.box.addLayout(left, 1)
        top = hbox(spacing=6)
        left.addLayout(top)
        top.addWidget(label("Сессия:", "page"))
        self.game_box = QComboBox()
        self.game_box.setMinimumWidth(320)
        self.game_box.activated.connect(lambda _i: self.load_signups())
        top.addWidget(self.game_box)
        self.status_box = QComboBox()
        self.status_box.addItems(self.STATUS_FILTER)
        self.status_box.activated.connect(lambda _i: self.load_signups())
        top.addWidget(self.status_box)
        top.addStretch()
        self.seats = QWidget()
        self.seats_layout = hbox(self.seats, spacing=10)
        top.addWidget(self.seats)

        self.table = RowTable(
            [
                ("Персонаж", 180, True),
                ("Игрок", 110, False),
                ("Комментарий", 130, True),
                ("Подана", 95, False),
                ("Статус", 140, False),
                ("Действия", 230, False),
            ],
            on_select=self.on_select,
        )
        left.addWidget(self.table, 1)
        self.blocked = Banner()
        left.addWidget(self.blocked)

        info_card = Card("Карточка персонажа", "только чтение")
        info_card.setFixedWidth(300)
        self.box.addWidget(info_card)
        body = info_card.body
        self.char_name = label("", "name", wrap=True)
        body.addWidget(self.char_name)
        self.char_owner = label("", "muted")
        body.addWidget(self.char_owner)
        body.addSpacing(10)
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(4)
        self.char_fields = {}
        for row, name in enumerate(("Раса", "Класс", "Уровень")):
            grid.addWidget(label(name, "muted"), row, 0)
            self.char_fields[name] = label()
            grid.addWidget(self.char_fields[name], row, 1)
        grid.setColumnStretch(1, 1)
        body.addLayout(grid)
        body.addSpacing(14)
        body.addWidget(label("ПРЕДЫСТОРИЯ", "caps"))
        self.char_story = label("", wrap=True)
        self.char_story.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        body.addWidget(self.char_story)
        body.addStretch()

    def refresh(self):
        """Перечитывает список своих сессий и заявки выбранной сессии."""
        current = self.game_box.currentText()
        self.game_ids = {
            f"{g['title']}  {to_short(g['scheduled_at'])}": g["id"]
            for g in self.my_games()
        }
        self.game_box.clear()
        self.game_box.addItems(list(self.game_ids))
        if current in self.game_ids:
            self.game_box.setCurrentText(current)
        self.load_signups()

    def show_character(self, char) -> None:
        """Заполняет карточку персонажа (или очищает, если char = None)."""
        self.char_name.setText(char["name"] if char else "Выберите заявку")
        self.char_owner.setText(f"Игрок: {char['owner_name']}" if char else "")
        values = {
            "Раса": char["race"] if char else "",
            "Класс": char["class"] if char else "",
            "Уровень": char["level"] if char else "",
        }
        for name, value in values.items():
            self.char_fields[name].setText(str(value or "—"))
        self.char_story.setText((char["backstory"] if char else "") or "—")

    def show_seats(self, game) -> None:
        """Показывает места полоской заполненности: «▬▬▬ Свободно: 2 из 5»."""
        clear_layout(self.seats_layout)
        if game is None:
            self.seats_layout.addWidget(label("Нет предстоящих сессий", "page"))
            return
        free = free_of(game)
        self.seats_layout.addWidget(
            SeatsBar(game["confirmed"], game["max_players"], 110)
        )
        self.seats_layout.addWidget(
            label(f"Свободно: {free} из {game['max_players']}", "green")
        )

    def load_signups(self):
        """Показывает заявки выбранной сессии."""
        self.show_character(None)
        self.blocked.hide()
        self.table.clear(
            "Заявок на эту сессию пока нет.\nИгроки увидят её на витрине сессий."
        )
        game_id = self.game_ids.get(self.game_box.currentText())
        if game_id is None:
            self.show_seats(None)
            self.status("")
            return
        game = games.get_game(self.app.conn, game_id)
        free = free_of(game)
        self.show_seats(game)

        status_filter = self.status_box.currentText()
        self.rows = {}
        has_pending = False
        queue = signups.queue_positions(self.app.conn, game_id)  # лист ожидания
        for row in signups.list_for_game(self.app.conn, game_id):
            status = signups.STATUS_NAMES[row["status"]]
            if status_filter != "Все статусы" and status != status_filter:
                continue
            self.rows[row["id"]] = row
            pending = row["status"] == "PENDING"
            has_pending = has_pending or pending
            if pending:
                # Автоматическая блокировка подтверждения при достижении лимита.
                actions = (
                    "buttons",
                    [
                        (
                            "✓ Подтвердить",
                            "accent",
                            lambda i=row["id"]: self.on_confirm(i),
                            free > 0,
                            "Мест нет: отклоните заявку, дождитесь, пока место "
                            "освободится, или увеличьте лимит во вкладке "
                            "«Расписание»",
                        ),
                        (
                            "Отклонить",
                            "danger",
                            lambda i=row["id"]: self.on_reject(i),
                            True,
                        ),
                    ],
                )
            else:
                actions = ("muted", to_short(row["decided_at"]))
            self.table.add(
                row["id"],
                [
                    (
                        "line",
                        [
                            ("bold", row["character_name"]),
                            (
                                "muted",
                                f"· {row['character_class'] or ''} "
                                f"{row['character_level']}",
                            ),
                        ],
                    ),
                    short_name(row["player_name"]),
                    ("muted", row["comment"] or "—"),
                    to_short(row["created_at"]),
                    (
                        "stack",
                        [("pill", status, STATUS_PILL[row["status"]])]
                        + ([("muted", row["reason"])] if row["reason"] else [])
                        + (
                            [("muted", f"№{queue[row['id']]} в очереди")]
                            if row["id"] in queue
                            else []
                        ),
                    ),
                    actions,
                ],
                sort=[
                    row["character_name"].lower(),
                    row["player_name"].lower(),
                    row["comment"] or "",
                    row["created_at"],
                    row["status"],
                    row["decided_at"] or "",
                ],
                highlight=pending,
            )
        counts = [
            sum(1 for r in self.rows.values() if r["status"] == code)
            for code in ("PENDING", "CONFIRMED", "REJECTED")
        ]
        self.status(
            f"На рассмотрении: {counts[0]}      Подтверждено: {counts[1]}      "
            f"Отклонено: {counts[2]}"
        )
        if free <= 0 and has_pending:
            self.blocked.show_message(
                f"Подтвердить заявку нельзя. На «{game['title']}» уже подтверждено "
                f"{game['confirmed']} заявок из {game['max_players']}. Новые "
                "заявки стоят в очереди: когда место освободится, подтвердите "
                "первую. Можно также увеличить лимит мест во вкладке «Расписание»."
            )

    def on_select(self, signup_id):
        """Показывает карточку персонажа из выбранной заявки."""
        char_id = self.rows[signup_id]["character_id"]
        self.show_character(characters.get_character(self.app.conn, char_id))

    def on_confirm(self, signup_id):
        """Подтверждает заявку."""
        signups.confirm_signup(self.app.conn, self.app.user, signup_id)
        self.load_signups()
        self.main.update_badges()

    def on_reject(self, signup_id):
        """Отклоняет заявку; причину отказа можно указать (её увидит Игрок)."""
        reason = ask_text(self, "Отклонить заявку", "Причина отказа (необязательно)")
        if reason is None:
            return
        signups.reject_signup(self.app.conn, self.app.user, signup_id, reason)
        self.load_signups()
        self.main.update_badges()


class GameNotesTab(FormGuard, GMTab):
    """Вкладка «Сюжетный блокнот»: заметка к выбранной сессии (макет 05)."""

    def __init__(self, main, app):
        """Создаёт список сессий и редактор заметки.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app, "h")
        self.game_id = None

        # Слева — поиск по названию и тексту заметки и список сессий.
        left = vbox(spacing=4)
        self.box.addLayout(left)
        left.addWidget(label("⌕ Поиск по заметкам", "page"))
        self.search = QLineEdit()
        self.search.textChanged.connect(lambda _text: self.refresh())
        left.addWidget(self.search)
        left.addSpacing(6)
        self.table = RowTable([("Сессии", 290, True)], on_select=self.on_select)
        self.table.setFixedWidth(300)
        left.addWidget(self.table, 1)

        right = Card()
        self.box.addWidget(right, 1)
        body = right.body
        head = hbox(spacing=6)
        self.title_label = label("Выберите сессию слева", "bold")
        head.addWidget(self.title_label)
        self.date_label = label("", "muted")
        head.addWidget(self.date_label)
        head.addStretch()
        head.addWidget(label("видно только Мастеру", "small"))
        body.addLayout(head)
        body.addSpacing(8)
        body.addWidget(hline())
        body.addSpacing(8)
        team_row = hbox(spacing=6)
        self.team = hbox(spacing=6)
        team_row.addLayout(self.team)
        team_row.addStretch()
        team_row.addWidget(button("Сохранить список", self.on_export, small=True))
        body.addLayout(team_row)
        body.addSpacing(8)
        self.editor = make_text(height=12, headings=True)
        body.addWidget(self.editor, 1)

        # Итоги прошедшей сессии (видны Игрокам) и повышение уровня участникам.
        self.summary_box = QWidget()
        summary = vbox(self.summary_box, spacing=4)
        summary.addSpacing(8)
        summary.addWidget(
            label("ИТОГИ ДЛЯ ИГРОКОВ — их увидят участники в «Мои записи»", "caps")
        )
        self.summary = make_text(height=3)
        summary.addWidget(self.summary)
        level_row = hbox(spacing=10)
        level_row.addWidget(
            button("Повысить уровень участникам (+1)", self.on_level_up, small=True)
        )
        self.levels_label = label("", "small")
        level_row.addWidget(self.levels_label)
        level_row.addStretch()
        summary.addLayout(level_row)
        body.addWidget(self.summary_box)

        # Кубики: Мастеру не нужно искать их во время игры.
        dice_row = hbox(spacing=4)
        dice_row.setContentsMargins(0, 10, 0, 0)
        dice_row.addWidget(label("Бросок:", "muted"))
        self.dice_count = QSpinBox()
        self.dice_count.setRange(1, 10)
        self.dice_count.setFixedWidth(80)
        dice_row.addWidget(self.dice_count)
        dice_row.addWidget(label("×", "muted"))
        for sides in dice.SIDES:
            dice_row.addWidget(
                button(f"d{sides}", lambda s=sides: self.on_roll(s), small=True)
            )
        self.dice_result = label("", "bold")
        dice_row.addSpacing(8)
        dice_row.addWidget(self.dice_result)
        dice_row.addStretch()
        body.addLayout(dice_row)

        bottom = hbox(spacing=6)
        bottom.setContentsMargins(0, 10, 0, 0)
        self.updated = label("", "small")
        bottom.addWidget(self.updated)
        bottom.addStretch()
        bottom.addWidget(button("Удалить заметку", self.on_delete, "danger"))
        bottom.addWidget(button("Отменить правки", self.reload))
        bottom.addWidget(button("Сохранить", self.on_save, "accent"))
        body.addLayout(bottom)
        self.summary_box.hide()
        self.remember()

    def refresh(self):
        """Перечитывает список своих предстоящих и прошедших сессий."""
        conn, user = self.app.conn, self.app.user
        query = self.search.text().strip()
        found = notes.search_game_notes(conn, user, query) if query else None
        if query:
            self.table.clear("Ничего не найдено.\nИзмените текст поиска.")
        else:
            self.table.clear("Сессий нет.\nСоздайте сессию во вкладке «Расписание».")
        for game in self.my_games() + self.my_games("CLOSED"):
            if found is not None and game["id"] not in found:
                continue
            note = notes.get_game_note(conn, user, game["id"])
            if game["status"] == "CLOSED":
                state = "прошла"
            else:
                state = "заметка есть" if note and note["content"] else "пусто"
            when = to_show(game["scheduled_at"])
            title = ("muted" if game["status"] == "CLOSED" else "bold", game["title"])
            self.table.add(
                game["id"], [("stack", [title, ("muted", f"{when} · {state}")])]
            )
        if self.game_id in self.table.rows:
            self.table.select(self.game_id, notify=False)

    def form_state(self):
        """Текст заметки и итогов — чтобы заметить несохранённые правки."""
        return (get_text(self.editor), get_text(self.summary))

    def on_roll(self, sides):
        """Бросает кубики и показывает результат: «2d6: 3 + 5 = 8»."""
        count = self.dice_count.value()
        values = dice.roll(sides, count)
        if count == 1:
            text = f"d{sides}: {values[0]}"
        else:
            text = f"{count}d{sides}: {' + '.join(map(str, values))} = {sum(values)}"
        self.dice_result.setText(text)

    def on_level_up(self):
        """Повышает на 1 уровень всех подтверждённых участников прошедшей сессии."""
        if not self.can_leave():
            return
        question = "Повысить на 1 уровень всех подтверждённых участников этой сессии?"
        if not ask(self, "Повышение уровня", question):
            return
        count = characters.level_up_after_game(
            self.app.conn, self.app.user, self.game_id
        )
        info(self, "Повышение уровня", f"Новый уровень получили персонажей: {count}.")
        self.reload()

    def discard(self):
        """Отбрасывает правки заметки."""
        self.reload()

    def on_select(self, game_id):
        """Запоминает выбранную сессию и показывает её заметку (сценарий 11)."""
        if game_id != self.game_id and not self.can_leave():
            self.table.select(self.game_id, notify=False)
            return
        self.game_id = game_id
        self.reload()

    def on_export(self):
        """Сохраняет состав сессии в файл CSV, чтобы распечатать перед игрой."""
        if self.game_id is None:
            raise ValidationError("Сессия", "Выберите сессию в списке слева.")
        game = games.get_game(self.app.conn, self.game_id)
        safe_title = re.sub(r'[\\/:*?"<>|]', "", game["title"])
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Список участников",
            f"Участники — {safe_title}.csv",
            "Таблица CSV (Excel) (*.csv)",
        )
        if not path:
            return
        count = signups.export_participants(
            self.app.conn, self.app.user, self.game_id, path
        )
        info(self, "Список участников", f"Сохранено участников: {count}\n{path}")

    def reload(self):
        """Показывает заметку и состав выбранной сессии."""
        if self.game_id is None:
            return
        game = games.get_game(self.app.conn, self.game_id)
        self.title_label.setText(game["title"])
        self.date_label.setText(f"· {to_show(game['scheduled_at'])}")
        clear_layout(self.team)
        self.team.addWidget(label("СОСТАВ", "caps"))
        team = [
            row
            for row in signups.list_for_game(self.app.conn, self.game_id)
            if row["status"] == "CONFIRMED"
        ]
        for row in team:
            text = f"{row['character_name']}  {row['character_class'] or ''} " + str(
                row["character_level"]
            )
            self.team.addWidget(Pill(text, "chip"))
        if not team:
            self.team.addWidget(label("пока никого", "muted"))
        note = notes.get_game_note(self.app.conn, self.app.user, self.game_id)
        set_text(self.editor, note["content"] if note else "")
        changed = to_show(note["updated_at"]) if note else "—"
        self.updated.setText(f"Изменено автоматически: {changed}")
        # Итоги и повышение уровня — только у прошедшей сессии.
        if game["status"] == "CLOSED":
            self.summary_box.show()
            set_text(self.summary, game["summary"] or "")
            self.levels_label.setText(
                "уровни за эту сессию уже повышены" if game["levels_given"] else ""
            )
        else:
            self.summary_box.hide()
            set_text(self.summary, "")
        self.remember()

    def on_save(self):
        """Сохраняет заметку и итоги (у прошедшей сессии) выбранной сессии."""
        if self.game_id is None:
            raise ValidationError("Сессия", "Выберите сессию в списке слева.")
        if games.get_game(self.app.conn, self.game_id)["status"] == "CLOSED":
            games.save_summary(
                self.app.conn, self.app.user, self.game_id, get_text(self.summary)
            )
        updated_at = notes.save_game_note(
            self.app.conn, self.app.user, self.game_id, get_text(self.editor)
        )
        self.updated.setText(f"Изменено автоматически: {to_show(updated_at)}")
        self.remember()
        self.refresh()

    def on_delete(self):
        """Удаляет заметку выбранной сессии после подтверждения."""
        if self.game_id is None:
            raise ValidationError("Сессия", "Выберите сессию в списке слева.")
        if ask(self, "Сюжетный блокнот", "Удалить заметку к этой сессии?"):
            notes.delete_game_note(self.app.conn, self.app.user, self.game_id)
            set_text(self.editor, "")
            self.updated.setText("Изменено автоматически: —")
            self.remember()
            self.refresh()


class WorldTab(FormGuard, GMTab):
    """Вкладка «База мира»: лор, NPC и локации (макет 06)."""

    FILTERS = [("Все", ""), ("Лор", "LORE"), ("NPC", "NPC"), ("Локации", "LOCATION")]

    def __init__(self, main, app):
        """Создаёт фильтры, список записей и форму записи.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app)
        self.note_id = None

        top = hbox(spacing=6)
        self.box.addLayout(top)
        self.filter_bar = Segmented(self.FILTERS, "", self.refresh)
        top.addWidget(self.filter_bar)
        top.addSpacing(12)
        top.addWidget(label("⌕ Поиск по заголовку", "page"))
        self.search = QLineEdit()
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(lambda _text: self.refresh())
        top.addWidget(self.search)
        top.addStretch()
        top.addWidget(button("+ Новая запись", self.on_new, "accent"))

        body = hbox(spacing=16)
        self.box.addLayout(body, 1)
        self.table = RowTable([("Записи", 330, True)], header=False)
        self.table.on_select = self.on_select
        self.table.setFixedWidth(340)
        body.addWidget(self.table)

        form_card = Card()
        body.addWidget(form_card, 1)
        form = form_card.body
        row = hbox(spacing=12)
        title_box, category_box = vbox(spacing=2), vbox(spacing=2)
        row.addLayout(title_box, 1)
        row.addLayout(category_box)
        field(title_box, "Заголовок *")
        self.title_entry = QLineEdit()
        title_box.addWidget(self.title_entry)
        field(category_box, "Категория *")
        self.category = QComboBox()
        self.category.addItems([""] + list(notes.CATEGORY_NAMES.values()))
        self.category.setMinimumWidth(180)
        category_box.addWidget(self.category)
        form.addLayout(row)
        form.addSpacing(12)
        self.content = make_text(height=12, headings=True)
        form.addWidget(self.content, 1)
        form.addSpacing(10)
        self.error = Banner()
        form.addWidget(self.error)
        bottom = hbox(spacing=6)
        bottom.setContentsMargins(0, 10, 0, 0)
        self.updated = label("", "small")
        bottom.addWidget(self.updated)
        bottom.addStretch()
        bottom.addWidget(button("Удалить", self.on_delete, "danger"))
        bottom.addWidget(button("Сохранить", self.on_save, "accent"))
        form.addLayout(bottom)
        self.clear_form()

    def refresh(self):
        """Перечитывает свои записи с учётом фильтра и поиска."""
        conn, user = self.app.conn, self.app.user
        everything = notes.list_world_notes(conn, user)
        # Подписи фильтров с количеством записей: «NPC · 6».
        for widget, (name, code) in zip(self.filter_bar.buttons, self.FILTERS):
            count = sum(1 for n in everything if not code or n["category"] == code)
            widget.setText(f"{name} · {count}")
        self.table.clear("Записей нет.\nНажмите «+ Новая запись».")
        rows = notes.list_world_notes(
            conn, user, self.filter_bar.value() or None, self.search.text()
        )
        for row in rows:
            first_line = (row["content"] or "").strip().split("\n")[0][:60]
            parts = [
                ("small", notes.CATEGORY_NAMES[row["category"]].upper()),
                ("bold", row["title"]),
            ]
            if first_line:
                parts.append(("muted", first_line))
            self.table.add(row["id"], [("stack", parts)])
        if self.note_id in self.table.rows:
            self.table.select(self.note_id, notify=False)

    def clear_form(self):
        """Очищает форму для новой записи."""
        self.note_id = None
        self.title_entry.clear()
        self.category.setCurrentIndex(0)
        set_text(self.content, "")
        self.updated.setText("Новая запись")
        self.error.hide()
        self.refresh()
        self.title_entry.setFocus()
        self.remember()

    def form_state(self):
        """Значения полей записи — чтобы заметить несохранённые правки."""
        return (
            self.title_entry.text(),
            self.category.currentText(),
            get_text(self.content),
        )

    def discard(self):
        """Отбрасывает правки записи."""
        if self.note_id is None:
            self.clear_form()
        else:
            self.load_note(self.note_id)

    def on_new(self):
        """Кнопка «+ Новая запись»: пустая форма (с вопросом о правках)."""
        if self.can_leave():
            self.clear_form()

    def on_select(self, note_id):
        """Загружает выбранную запись (спросив о несохранённых правках)."""
        if note_id != self.note_id and not self.can_leave():
            self.table.select(self.note_id, notify=False)
            return
        self.load_note(note_id)

    def load_note(self, note_id):
        """Загружает запись в форму."""
        row = notes.get_world_note(self.app.conn, self.app.user, note_id)
        self.note_id = note_id
        self.title_entry.setText(row["title"])
        self.category.setCurrentText(notes.CATEGORY_NAMES[row["category"]])
        set_text(self.content, row["content"])
        self.updated.setText(f"Изменено: {to_show(row['updated_at'])}")
        self.error.hide()
        self.table.select(note_id, notify=False)
        self.remember()

    def on_save(self):
        """Сохраняет запись из формы; ошибку показывает в форме."""
        codes = {name: code for code, name in notes.CATEGORY_NAMES.items()}
        try:
            self.note_id = notes.save_world_note(
                self.app.conn,
                self.app.user,
                codes.get(self.category.currentText()),
                self.title_entry.text(),
                get_text(self.content),
                self.note_id,
            )
        except ValidationError as error:
            self.error.show_message(error.message)
            return
        self.error.hide()
        self.remember()
        self.refresh()

    def on_delete(self):
        """Удаляет выбранную запись после подтверждения."""
        if self.note_id is None:
            raise ValidationError("Запись", "Выберите запись в списке.")
        if ask(self, "База мира", "Удалить эту запись?"):
            notes.delete_world_note(self.app.conn, self.app.user, self.note_id)
            self.clear_form()


class StatsTab(GMTab):
    """Вкладка «Статистика»: итоги работы Мастера."""

    CARDS = [
        ("planned", "предстоящих сессий"),
        ("closed", "проведено сессий"),
        ("cancelled", "отменено"),
        ("fill", "средняя заполняемость"),
    ]

    def __init__(self, main, app):
        """Создаёт карточки с числами и две таблицы.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app)
        numbers = hbox(spacing=12)
        self.box.addLayout(numbers)
        self.values = {}
        for key, caption in self.CARDS:
            box = Card()
            self.values[key] = label("", "number")
            box.body.addWidget(self.values[key])
            box.body.addWidget(label(caption, "muted"))
            numbers.addWidget(box, 1)

        tables = hbox(spacing=16)
        self.box.addLayout(tables, 1)
        left = vbox(spacing=6)
        tables.addLayout(left, 1)
        left.addWidget(label("Самые активные игроки", "page_bold"))
        self.players = RowTable([("Игрок", 260, True), ("Подтверждено", 130, False)])
        left.addWidget(self.players, 1)
        right = vbox(spacing=6)
        tables.addLayout(right, 1)
        right.addWidget(label("Прошедшие сессии", "page_bold"))
        self.past = RowTable(
            [("Сессия", 240, True), ("Дата", 150, False), ("Участники", 130, False)]
        )
        right.addWidget(self.past, 1)

    def refresh(self):
        """Пересчитывает статистику текущего Мастера."""
        stats = games.master_stats(self.app.conn, self.app.user)
        for key, _ in self.CARDS:
            value = stats[key]
            if key == "fill":
                value = "—" if value is None else f"{value} %"
            self.values[key].setText(str(value))
        self.players.clear("Подтверждённых заявок пока нет.")
        for number, (name, count) in enumerate(stats["players"], start=1):
            self.players.add(number, [("bold", name), count])
        self.past.clear("Прошедших сессий пока нет.")
        for game in games.list_games(self.app.conn, "CLOSED", self.app.user["id"]):
            self.past.add(
                game["id"],
                [
                    ("bold", game["title"]),
                    to_show(game["scheduled_at"]),
                    f"{game['confirmed']} из {game['max_players']}",
                ],
            )
        self.status("Статистика считается по всем вашим сессиям")


class CalendarTab(GMTab):
    """Вкладка «Календарь»: сессии Мастера по дням месяца."""

    SHOWN = 3  # сколько сессий помещается в клетку дня

    def __init__(self, main, app):
        """Создаёт заголовок с переключением месяцев и сетку дней.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app)
        today = month.today()
        self.year, self.month = today.year, today.month
        top = hbox(spacing=8)
        self.box.addLayout(top)
        top.addWidget(button("‹", lambda: self.turn(-1)))
        self.caption = label("", "page_bold")
        self.caption.setFixedWidth(150)
        self.caption.setAlignment(Qt.AlignCenter)
        top.addWidget(self.caption)
        top.addWidget(button("›", lambda: self.turn(1)))
        top.addSpacing(6)
        top.addWidget(button("Сегодня", self.go_today))
        top.addStretch()
        top.addWidget(
            label(
                "чёрным — предстоящие, серым — прошедшие; щелчок открывает сессию",
                "page",
            )
        )
        self.grid_box = None

    def turn(self, delta: int) -> None:
        """Кнопки ‹ › — предыдущий или следующий месяц."""
        self.year, self.month = month.shift_month(self.year, self.month, delta)
        self.refresh()

    def go_today(self) -> None:
        """Кнопка «Сегодня» — текущий месяц."""
        today = month.today()
        self.year, self.month = today.year, today.month
        self.refresh()

    def refresh(self):
        """Рисует месяц: в каждом дне — его сессии по времени."""
        self.caption.setText(month.title(self.year, self.month))
        if self.grid_box is not None:
            self.grid_box.hide()
            self.grid_box.deleteLater()
        self.grid_box = QWidget()
        grid = QGridLayout(self.grid_box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)
        self.box.addWidget(self.grid_box, 1)
        for column, name in enumerate(month.WEEKDAYS):
            grid.addWidget(label(name, "page"), 0, column)
            grid.setColumnStretch(column, 1)
        sessions = self.my_games() + self.my_games("CLOSED")
        by_day = month.games_by_day(sessions)
        today = month.today()
        weeks = month.month_grid(self.year, self.month)
        count = 0
        for row, week in enumerate(weeks, start=1):
            grid.setRowStretch(row, 1)
            for column, day in enumerate(week):
                if day is None:
                    continue
                cell = QFrame()
                cell.setObjectName("day")
                bg = c("green_soft") if day == today else c("bg")
                cell.setStyleSheet(
                    f"QFrame#day {{ background: {bg}; border: 1px solid {c('line')}; "
                    "border-radius: 4px; }"
                )
                lines = vbox(cell, margins=(6, 4, 6, 4), spacing=1)
                lines.addWidget(label(str(day.day), "bold" if day == today else None))
                day_games = by_day.get(day, [])
                count += len(day_games)
                for game in day_games[: self.SHOWN]:
                    time = game["scheduled_at"][11:]
                    item = ClickLabel(
                        f"{time} {game['title']}",
                        "small" if game["status"] == "CLOSED" else None,
                    )
                    if game["status"] != "CLOSED":
                        item.setStyleSheet("font-size: 9pt;")
                    item.setWordWrap(True)
                    item.clicked.connect(lambda g=game: self.open_game(g))
                    item.setToolTip(
                        f"{game['title']}\n{to_show(game['scheduled_at'])} · "
                        f"занято {game['confirmed']} из {game['max_players']}"
                    )
                    lines.addWidget(item)
                if len(day_games) > self.SHOWN:
                    lines.addWidget(
                        label(f"ещё {len(day_games) - self.SHOWN}", "small")
                    )
                lines.addStretch()
                grid.addWidget(cell, row, column)
        self.status(f"Сессий в этом месяце: {count}")

    def open_game(self, game) -> None:
        """Открывает сессию во вкладке «Расписание» для изменения."""
        self.main.show_tab(0)
        schedule = self.main.tabs[0]
        schedule.period.set_value(game["status"])
        schedule.refresh()
        schedule.on_select(game["id"])
