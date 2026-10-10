"""Окно Игрока: вкладки «Витрина сессий», «Мои записи», «Мои персонажи».

Макеты 07–09. Игрок выбирает Мастера (можно найти по имени) и видит
витрину его сессий. Вкладок «Сюжетный блокнот» и «База мира» здесь нет
(сценарий 12 п. 6.1 ТЗ).
"""

from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLineEdit, QWidget

from gm_hub.config import now_str, to_short, to_show
from gm_hub.logic import auth, characters, games, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.settings import get_setting, write_setting
from gm_hub.ui.common import (
    Banner,
    Card,
    ChoiceCards,
    FormGuard,
    MainFrame,
    Segmented,
    Tab,
    ask,
    button,
    field,
    get_text,
    hbox,
    is_soon,
    label,
    make_text,
    set_text,
    vbox,
)
from gm_hub.ui.table import STATUS_PILL, RowTable


def character_info(c) -> str:
    """Возвращает подпись персонажа: «Полурослик · Плут · 4 ур.»."""
    return f"{c['race'] or '—'} · {c['class'] or '—'} · {c['level']} ур."


def status_cell(row):
    """Статус заявки таблеткой, под ним — причина отказа, если она есть."""
    if row["game_status"] == "CANCELLED":
        pill = ("pill", "Сессия отменена", "bad")
    else:
        pill = ("pill", signups.STATUS_NAMES[row["status"]], STATUS_PILL[row["status"]])
    reason = row["reason"] if row["reason"] != "Сессия отменена" else None
    return ("stack", [pill] + ([("muted", reason)] if reason else []))


class PlayerFrame(MainFrame):
    """Главное окно Игрока с вкладками."""

    def __init__(self, app):
        """Создаёт шапку и вкладки.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(
            app,
            "Кабинет Игрока",
            [
                ("Витрина сессий", ShowcaseTab),
                ("Мои записи", MySignupsTab),
                ("Мои персонажи", CharactersTab),
            ],
        )

    def update_badges(self) -> None:
        """Пишет на вкладке «Мои записи» число новых решений Мастеров."""
        self.set_badge(1, signups.count_new_decisions(self.app.conn, self.app.user))


class ShowcaseTab(Tab):
    """Вкладка «Витрина сессий»: выбор Мастера и запись на игру (макет 07)."""

    def __init__(self, main, app):
        """Создаёт список Мастеров, таблицу сессий и форму заявки.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app)
        self.master_id = None
        self.master_key = "master_" + app.user["login"]  # выбор Мастера

        # Над всем — напоминание о ближайшей подтверждённой игре.
        self.reminder = Banner()
        self.box.addWidget(self.reminder)
        body = hbox(spacing=16)
        self.box.addLayout(body, 1)

        # Слева — выбор Мастера с поиском по имени.
        left = vbox(spacing=4)
        body.addLayout(left)
        left.addWidget(label("Мастер", "page_bold"))
        left.addWidget(label("⌕ найти по имени", "page"))
        self.search = QLineEdit()
        self.search.textChanged.connect(lambda _text: self.load_masters())
        left.addWidget(self.search)
        left.addSpacing(6)
        self.masters = RowTable(
            [("Мастера", 200, True)], header=False, on_select=self.on_master
        )
        self.masters.setFixedWidth(210)
        left.addWidget(self.masters, 1)

        center = vbox(spacing=10)
        body.addLayout(center, 1)
        self.master_label = label("", "heading")
        center.addWidget(self.master_label)
        # Фильтры витрины: период по дате и только сессии со свободными местами.
        filters = hbox(spacing=6)
        center.addLayout(filters)
        self.period = Segmented(
            [(name, name) for name in games.PERIOD_DAYS], "Все даты", self.load_games
        )
        filters.addWidget(self.period)
        filters.addStretch()
        self.only_free = QCheckBox("Только со свободными местами")
        self.only_free.toggled.connect(lambda _on: self.load_games())
        filters.addWidget(self.only_free)
        self.table = RowTable(
            [
                ("Сессия", 240, True),
                ("Когда", 150, False),
                ("Свободно", 90, False),
                ("Моя заявка", 140, False),
            ],
            on_select=self.on_select,
            on_double=self.on_double,
        )
        center.addWidget(self.table, 1)

        form_card = Card("Запись на сессию")
        form_card.setFixedWidth(320)
        body.addWidget(form_card)
        form = form_card.body
        self.info_title = label("Выберите сессию в таблице", "bold", wrap=True)
        form.addWidget(self.info_title)
        self.info_when = label("", "muted", wrap=True)
        form.addWidget(self.info_when)
        field(form, "Персонаж *")
        self.characters = ChoiceCards()
        form.addWidget(self.characters)
        field(form, "Комментарий Мастеру (необязательно)")
        self.comment = QLineEdit()
        self.comment.returnPressed.connect(self.on_send)
        form.addWidget(self.comment)
        form.addSpacing(12)
        self.error = Banner()
        form.addWidget(self.error)
        form.addSpacing(4)
        self.send_button = button("Отправить заявку", self.on_send, "accent")
        form.addWidget(self.send_button)
        form.addSpacing(10)
        form.addWidget(
            label(
                "Без выбранного персонажа кнопка покажет:\n"
                "«Выберите персонажа для заявки».",
                "small",
            )
        )
        form.addStretch()

    def refresh(self):
        """Перечитывает Мастеров, витрину и список персонажей."""
        self.load_masters()
        self.characters.set_options(
            [
                (c["id"], c["name"], character_info(c))
                for c in characters.list_characters(self.app.conn, self.app.user)
            ]
        )
        self.error.hide()
        game = signups.next_game(self.app.conn, self.app.user)
        if game:
            self.reminder.show_message(
                f"Скоро игра: «{game['game_title']}» — "
                f"{to_show(game['scheduled_at'])}, Мастер {game['gm_name']}, "
                f"персонаж {game['character_name']}.",
                "ok",
                auto_hide=False,
            )
        else:
            self.reminder.hide()

    def load_masters(self):
        """Показывает Мастеров, подходящих под поиск по имени."""
        found = auth.list_masters(self.app.conn, self.search.text())
        self.masters.clear("Мастер не найден.\nПроверьте имя.")
        for master in found:
            count = len(games.list_games(self.app.conn, gm_id=master["id"]))
            self.masters.add(
                master["id"],
                [
                    (
                        "stack",
                        [
                            ("bold", master["full_name"]),
                            ("muted", f"предстоящих сессий: {count}"),
                        ],
                    )
                ],
            )
        ids = [m["id"] for m in found]
        if self.master_id is None:
            # при входе — Мастер, выбранный в прошлый раз
            self.master_id = get_setting(self.master_key)
        if self.master_id not in ids:
            self.master_id = ids[0] if ids else None
        if self.master_id is not None:
            self.masters.select(self.master_id, notify=False)
        self.load_games()

    def on_master(self, master_id):
        """Выбирает Мастера, запоминает выбор и показывает его сессии."""
        self.master_id = master_id
        try:
            write_setting(self.master_key, master_id)
        except OSError:
            pass  # файл настроек недоступен — просто не запоминаем
        self.load_games()

    def on_double(self, game_id):
        """Двойной щелчок по сессии: выбрать её и перейти к выбору персонажа."""
        self.table.select(game_id)
        options = list(self.characters.cards)
        if len(options) == 1:
            self.characters.select(options[0])  # единственный персонаж — сразу
        self.send_button.setFocus()

    def open_game(self, master_id, game_id):
        """Показывает сессию на витрине (переход из «Мои записи»)."""
        self.master_id = master_id
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.load_masters()
        if game_id in self.table.rows:
            self.table.select(game_id)

    def load_games(self):
        """Показывает предстоящие сессии выбранного Мастера."""
        conn, user = self.app.conn, self.app.user
        self.info_title.setText("Выберите сессию в таблице")
        self.info_when.setText("")
        if self.master_id is None:
            self.master_label.setText("Мастер не выбран")
            self.table.clear("Выберите Мастера в списке слева.")
            return
        master = next(m for m in auth.list_masters(conn) if m["id"] == self.master_id)
        self.master_label.setText(f"Сессии Мастера: {master['full_name']}")

        my_status = {}  # id сессии -> статусы моих заявок, главный — первым
        order = ["CONFIRMED", "PENDING", "REJECTED"]
        for row in signups.list_for_player(conn, user):
            my_status.setdefault(row["game_id"], []).append(row["status"])
        for statuses in my_status.values():
            statuses.sort(key=order.index)

        days = games.PERIOD_DAYS[self.period.value()]
        if days or self.only_free.isChecked():
            self.table.clear("Нет сессий под выбранные условия.\nСнимите фильтр.")
        else:
            self.table.clear("У этого Мастера нет предстоящих сессий")
        shown = 0
        for game in games.list_games(conn, gm_id=self.master_id):
            free = games.free_seats(game["max_players"], game["confirmed"])
            if self.only_free.isChecked() and free <= 0:
                continue
            if not games.in_period(game["scheduled_at"], days):
                continue
            title = [("bold", game["title"])]
            if game["description"]:
                title.append(("muted", game["description"]))
            when = [to_short(game["scheduled_at"])]
            if is_soon(game["scheduled_at"]):
                when.append(("pill", "СКОРО", "warn"))
            statuses = my_status.get(game["id"], [])
            shown += 1
            mine = (
                ("pill", signups.STATUS_NAMES[statuses[0]], STATUS_PILL[statuses[0]])
                if statuses
                else ("muted", "—")
            )
            self.table.add(
                game["id"],
                [
                    ("stack", title),
                    ("line", when),
                    (
                        ("bold", f"{free} из {game['max_players']}")
                        if free <= 0
                        else f"{free} из {game['max_players']}"
                    ),
                    mine,
                ],
                sort=[
                    game["title"].lower(),
                    game["scheduled_at"],
                    free,
                    statuses[0] if statuses else "",
                ],
            )
        self.status(f"Сессий у Мастера: {shown}")

    def on_select(self, game_id):
        """Показывает выбранную сессию в форме заявки."""
        game = games.get_game(self.app.conn, game_id)
        free = games.free_seats(game["max_players"], game["confirmed"])
        self.info_title.setText(game["title"])
        seats = (
            f"свободно {free} из {game['max_players']}"
            if free > 0
            else "мест нет — заявка встанет в очередь"
        )
        self.info_when.setText(f"{to_show(game['scheduled_at'])} · {seats}")
        self.send_button.setText("Отправить заявку" if free > 0 else "Встать в очередь")
        self.error.hide()

    def on_send(self):
        """Подаёт заявку выбранным персонажем (сценарии 5–7)."""
        game_id = self.table.selected
        try:
            signups.create_signup(
                self.app.conn,
                self.app.user,
                game_id,
                self.characters.get(),
                self.comment.text(),
            )
        except ValidationError as error:
            self.error.show_message(error.message)
            return
        title = games.get_game(self.app.conn, game_id)["title"]
        self.comment.clear()
        # Как в прототипе: после отправки открываются «Мои записи» с сообщением.
        self.main.show_tab(1)
        self.main.tabs[1].banner.show_message(
            f"Заявка на «{title}» отправлена. Статус: на рассмотрении.", "ok"
        )


class MySignupsTab(Tab):
    """Вкладка «Мои записи»: статусы своих заявок у всех Мастеров (макет 08)."""

    PERIODS = [("Предстоящие", "future"), ("Прошедшие", "past")]

    def __init__(self, main, app):
        """Создаёт таблицу заявок.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app)
        self.banner = Banner()
        self.box.addWidget(self.banner)
        top = hbox(spacing=6)
        self.box.addLayout(top)
        self.period = Segmented(self.PERIODS, "future", self.refresh)
        top.addWidget(self.period)
        top.addStretch()
        top.addWidget(button("Отозвать заявку", self.on_withdraw, "danger"))
        self.table = RowTable(
            [
                ("Сессия", 290, True),
                ("Когда", 150, False),
                ("Персонаж", 120, False),
                ("Мой комментарий", 200, True),
                ("Статус", 170, False),
                ("Решение", 120, False),
            ],
            on_double=self.on_double,
        )
        self.box.addWidget(self.table, 1)
        self.rows = {}  # id заявки -> строка заявки

    def on_double(self, signup_id):
        """Двойной щелчок по записи: открыть её сессию на витрине."""
        row = self.rows[signup_id]
        self.main.show_tab(0)
        self.main.tabs[0].open_game(row["gm_id"], row["game_id"])

    def refresh(self):
        """Перечитывает заявки текущего Игрока (сценарий 14)."""
        self.banner.hide()
        self.table.clear(
            "Заявок пока нет.\nЗапишитесь на игру во вкладке «Витрина сессий»."
        )
        rows = signups.list_for_player(self.app.conn, self.app.user)
        self.rows = {row["id"]: row for row in rows}
        now = now_str()
        # Решения, принятые после прошлого просмотра, отмечаются «новое».
        seen = signups.seen_at(self.app.conn, self.app.user) or ""
        queues = {}  # id сессии -> номера заявок в листе ожидания
        for row in rows:
            upcoming = row["scheduled_at"] >= now
            if upcoming != (self.period.value() == "future"):
                continue
            decision = [("muted", to_short(row["decided_at"]))]
            if row["decided_at"] and row["decided_at"] > seen:
                decision.append(("pill", "новое", "warn"))
            title = [
                ("bold", row["game_title"]),
                ("muted", f"Мастер: {row['gm_name']}"),
            ]
            # Итоги прошедшей игры Мастер пишет для её участников.
            if row["game_summary"] and row["status"] == "CONFIRMED":
                title.append(("muted", f"Итоги: {row['game_summary']}"))
            status = status_cell(row)
            if row["status"] == "PENDING":
                if row["game_id"] not in queues:
                    queues[row["game_id"]] = signups.queue_positions(
                        self.app.conn, row["game_id"]
                    )
                number = queues[row["game_id"]].get(row["id"])
                if number:
                    status[1].append(("muted", f"в очереди: №{number}"))
            self.table.add(
                row["id"],
                [
                    ("stack", title),
                    to_show(row["scheduled_at"]),
                    row["character_name"],
                    ("muted", row["comment"] or "—"),
                    status,
                    ("stack", decision),
                ],
                sort=[
                    row["game_title"].lower(),
                    row["scheduled_at"],
                    row["character_name"].lower(),
                    row["comment"] or "",
                    row["status"],
                    row["decided_at"] or "",
                ],
                highlight=row["status"] == "PENDING",
            )
        confirmed = [r for r in rows if r["status"] == "CONFIRMED"]
        pending = [r for r in rows if r["status"] == "PENDING"]
        upcoming = [r for r in confirmed if r["scheduled_at"] >= now]
        nearest = (
            f"{to_short(upcoming[0]['scheduled_at'])} · {upcoming[0]['game_title']}"
            if upcoming
            else "—"
        )
        self.status(
            f"Подтверждено: {len(confirmed)}      Ждут решения: {len(pending)}      "
            f"Ближайшая игра: {nearest}"
        )
        signups.mark_decisions_seen(self.app.conn, self.app.user)

    def on_withdraw(self):
        """Отзывает выбранную заявку после подтверждения."""
        signup_id = self.table.selected
        if signup_id is None:
            raise ValidationError("Заявка", "Выберите заявку в таблице.")
        if ask(self, "Мои записи", "Отозвать выбранную заявку?"):
            signups.withdraw_signup(self.app.conn, self.app.user, signup_id)
            self.refresh()


class CharactersTab(FormGuard, Tab):
    """Вкладка «Мои персонажи»: карточки персонажей (макет 09)."""

    def __init__(self, main, app):
        """Создаёт список персонажей и форму карточки.

        Args:
            main: Окно кабинета.
            app: Приложение.
        """
        super().__init__(main, app, "h")
        self.character_id = None
        self.level = 1

        left = Card("Персонажи", action=("+ Новый", self.on_new), padding=0)
        left.setFixedWidth(310)
        self.box.addWidget(left)
        self.table = RowTable(
            [("Персонаж", 300, True)],
            header=False,
            on_select=self.on_select,
            flat=True,
        )
        left.body.addWidget(self.table, 1)

        form_card = Card()
        self.box.addWidget(form_card, 1)
        form = form_card.body
        row = QGridLayout()
        row.setHorizontalSpacing(12)
        boxes = [QWidget() for _ in range(3)]
        layouts = [vbox(box, spacing=2) for box in boxes]
        for index, box in enumerate(boxes):
            row.addWidget(box, 0, index)
            row.setColumnStretch(index, 1)  # три поля одинаковой ширины
        field(layouts[0], "Имя *")
        self.name = QLineEdit()
        layouts[0].addWidget(self.name)
        field(layouts[1], "Раса")
        self.race = QComboBox()
        self.race.setEditable(True)
        self.race.addItems(characters.RACES)
        layouts[1].addWidget(self.race)
        field(layouts[2], "Класс")
        self.cls = QComboBox()
        self.cls.setEditable(True)
        self.cls.addItems(characters.CLASSES)
        layouts[2].addWidget(self.cls)
        form.addLayout(row)
        field(form, "Предыстория")
        self.backstory = make_text(height=7)
        form.addWidget(self.backstory, 1)
        form.addSpacing(10)
        self.error = Banner()
        form.addWidget(self.error)
        buttons = hbox(spacing=6)
        buttons.setContentsMargins(0, 10, 0, 0)
        buttons.addWidget(button("Удалить персонажа", self.on_delete, "danger"))
        buttons.addStretch()
        buttons.addWidget(button("Отменить", self.reload))
        buttons.addWidget(button("Сохранить", self.on_save, "accent"))
        form.addLayout(buttons)
        self.clear_form()

    def refresh(self):
        """Перечитывает персонажей текущего Игрока с числом их заявок."""
        counts = {}  # id персонажа -> {статус: количество}
        for row in signups.list_for_player(self.app.conn, self.app.user):
            by_status = counts.setdefault(row["character_id"], {})
            by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        self.table.clear("Персонажей пока нет.\nНажмите «+ Новый».")
        for c in characters.list_characters(self.app.conn, self.app.user):
            parts = [("bold", c["name"]), ("muted", character_info(c))]
            by_status = counts.get(c["id"], {})
            if by_status.get("CONFIRMED"):
                parts.append(("pill", f"{by_status['CONFIRMED']} подтверждена", "ok"))
            if by_status.get("PENDING"):
                parts.append(
                    ("pill", f"{by_status['PENDING']} на рассмотрении", "warn")
                )
            self.table.add(c["id"], [("stack", parts)])
        if self.character_id in self.table.rows:
            self.table.select(self.character_id, notify=False)

    def clear_form(self):
        """Очищает форму для нового персонажа."""
        self.character_id = None
        self.name.clear()
        self.race.setCurrentText("")
        self.cls.setCurrentText("")
        # Уровень в карточке не выбирается: у нового персонажа он 1 (в БД поле
        # обязательное), у существующего сохраняется прежний.
        self.level = 1
        set_text(self.backstory, "")
        self.error.hide()
        self.refresh()
        self.name.setFocus()
        self.remember()

    def form_state(self):
        """Значения полей карточки — чтобы заметить несохранённые правки."""
        return (
            self.name.text(),
            self.race.currentText(),
            self.cls.currentText(),
            get_text(self.backstory),
        )

    def discard(self):
        """Отбрасывает правки карточки."""
        if self.character_id is None:
            self.clear_form()
        else:
            self.reload()

    def on_new(self):
        """Кнопка «+ Новый»: пустая карточка (с вопросом о правках)."""
        if self.can_leave():
            self.clear_form()

    def on_select(self, character_id):
        """Загружает выбранного персонажа (спросив о несохранённых правках)."""
        if character_id != self.character_id and not self.can_leave():
            self.table.select(self.character_id, notify=False)
            return
        self.character_id = character_id
        self.reload()

    def reload(self):
        """Загружает выбранного персонажа в форму (отменяет правки)."""
        if self.character_id is None:
            return
        c = characters.get_character(self.app.conn, self.character_id)
        self.name.setText(c["name"])
        self.race.setCurrentText(c["race"] or "")
        self.cls.setCurrentText(c["class"] or "")
        self.level = c["level"]
        set_text(self.backstory, c["backstory"])
        self.error.hide()
        self.table.select(self.character_id, notify=False)
        self.remember()

    def on_save(self):
        """Сохраняет карточку персонажа; ошибку показывает в форме."""
        if self.character_id is not None:
            # уровень мог повысить Мастер, пока карточка была открыта
            self.level = characters.get_character(self.app.conn, self.character_id)[
                "level"
            ]
        try:
            self.character_id = characters.save_character(
                self.app.conn,
                self.app.user,
                self.name.text(),
                self.race.currentText(),
                self.cls.currentText(),
                self.level,
                get_text(self.backstory),
                self.character_id,
            )
        except ValidationError as error:
            self.error.show_message(error.message)
            return
        self.error.show_message("Карточка персонажа сохранена.", "ok")
        self.remember()
        self.refresh()

    def on_delete(self):
        """Удаляет персонажа, если у него нет активных заявок (сценарий 13)."""
        if self.character_id is None:
            self.error.show_message("Выберите персонажа в списке.")
            return
        if not ask(self, "Мои персонажи", "Удалить выбранного персонажа?"):
            return
        try:
            characters.delete_character(self.app.conn, self.app.user, self.character_id)
        except ValidationError as error:
            self.error.show_message(error.message)
            return
        self.clear_form()
