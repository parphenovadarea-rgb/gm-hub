"""Окно Мастера: вкладки «Расписание», «Заявки», «Сюжетный блокнот», «База мира».

Макеты 03–06. У каждого Мастера своё окно: здесь видны только его сессии,
заявки на них, его заметки и его база мира.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.config import to_short, to_show
from gm_hub.logic import characters, games, notes, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    px,
    ask_text,
    GREEN_TEXT,
    PAGE,
    Banner,
    MainFrame,
    card,
    field,
    get_text,
    is_soon,
    make_text,
    segmented,
    set_text,
    short_name,
)
from gm_hub.ui.table import STATUS_PILL, Pill, RowTable


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
            ],
        )


class Tab(ttk.Frame):
    """Общая основа вкладки: серый фон и доступ к БД и пользователю."""

    def __init__(self, parent, app):
        """Создаёт вкладку.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=px(16), style="Page.TFrame")
        self.app = app

    def status(self, text: str) -> None:
        """Пишет итоги вкладки в строку внизу окна."""
        self.master.master.set_status(text)

    def my_games(self, status: str = "PLANNED"):
        """Возвращает сессии текущего Мастера с нужным статусом."""
        return games.list_games(self.app.conn, status, self.app.user["id"])


class ScheduleTab(Tab):
    """Вкладка «Расписание»: список сессий и форма сессии (макет 03)."""

    PERIODS = [
        ("Предстоящие", "PLANNED"),
        ("Прошедшие", "CLOSED"),
        ("Отменённые", "CANCELLED"),
    ]

    def __init__(self, parent, app):
        """Создаёт таблицу сессий и форму.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        self.game_id = None  # id сессии в форме, None — новая сессия

        form = card(self, "Новая сессия")
        form.master.pack(side="right", fill="y", padx=px((16, 0)))
        self.form = form

        top = ttk.Frame(self, style="Page.TFrame")
        top.pack(fill="x")
        self.period = tk.StringVar(value="PLANNED")
        segmented(top, self.PERIODS, self.period, self.refresh).pack(side="left")
        ttk.Button(
            top, text="Удалить", style="Danger.TButton", command=self.on_delete
        ).pack(side="right")
        ttk.Button(
            top, text="Отменить сессию", style="Danger.TButton", command=self.on_cancel
        ).pack(side="right", padx=px(6))
        ttk.Button(
            top, text="+ Новая сессия", style="Accent.TButton", command=self.clear_form
        ).pack(side="right")

        self.table = RowTable(
            self,
            [
                ("Название", 336, True),
                ("Дата и время", 157, False),
                ("Места", 168, False),
                ("Новых заявок", 123, False),
                ("Статус", 146, False),
            ],
            on_select=self.on_select,
        )
        self.table.pack(fill="both", expand=True, pady=px((12, 0)))

        field(form, "Название *")
        self.title_entry = ttk.Entry(form, width=34)
        self.title_entry.pack(fill="x")
        field(form, "Описание для игроков")
        self.description = make_text(form, height=3)
        self.description.pack(fill="x")
        row = ttk.Frame(form)
        row.pack(fill="x")
        date_box, time_box = ttk.Frame(row), ttk.Frame(row)
        date_box.pack(side="left", fill="x", expand=True, padx=px((0, 8)))
        time_box.pack(side="left", fill="x", expand=True)
        field(date_box, "Дата * (ДД.ММ.ГГГГ)")
        self.date_entry = ttk.Entry(date_box, width=14)
        self.date_entry.pack(fill="x")
        field(time_box, "Время * (ЧЧ:ММ)")
        self.time_entry = ttk.Entry(time_box, width=8)
        self.time_entry.pack(fill="x")
        field(form, "Лимит мест *")
        self.max_players = ttk.Spinbox(form, from_=1, to=50, width=8)
        self.max_players.pack(anchor="w")
        ttk.Label(form, text="Целое число больше нуля", style="Small.TLabel").pack(
            anchor="w"
        )
        self.save_button = ttk.Button(
            form, text="Опубликовать", style="Accent.TButton", command=self.on_save
        )
        self.save_button.pack(fill="x", pady=px((14, 0)))
        self.error = Banner(form, fill="x", pady=px((10, 0)), before=self.save_button)
        self.clear_form()

    def refresh(self):
        """Перечитывает сессии текущего Мастера из БД."""
        hints = {
            "PLANNED": "Предстоящих сессий пока нет.\n"
            "Нажмите «+ Новая сессия», чтобы опубликовать первую игру.",
            "CLOSED": "Прошедших сессий пока нет.",
            "CANCELLED": "Отменённых сессий нет.",
        }
        self.table.clear(hints[self.period.get()])
        for game in self.my_games(self.period.get()):
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
        self.form.title_label.config(text="Новая сессия")
        self.save_button.config(text="Опубликовать")
        self.title_entry.delete(0, "end")
        set_text(self.description, "")
        self.date_entry.delete(0, "end")
        self.time_entry.delete(0, "end")
        self.max_players.set(4)
        self.error.hide()
        self.refresh()

    def on_select(self, game_id):
        """Загружает выбранную сессию в форму для изменения."""
        game = games.get_game(self.app.conn, game_id)
        self.game_id = game_id
        self.form.title_label.config(text="Изменение сессии")
        self.save_button.config(text="Сохранить")
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, game["title"])
        set_text(self.description, game["description"])
        when = to_show(game["scheduled_at"])
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, when[:10])
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, when[11:])
        self.max_players.set(game["max_players"])
        self.error.hide()

    def on_save(self):
        """Сохраняет сессию из формы; ошибку показывает в форме."""
        try:
            games.save_game(
                self.app.conn,
                self.app.user,
                self.title_entry.get(),
                get_text(self.description),
                self.date_entry.get(),
                self.time_entry.get(),
                self.max_players.get(),
                self.game_id,
            )
        except ValidationError as error:
            self.error.show(error.message)
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
        if messagebox.askyesno("Отмена сессии", "Отменить выбранную сессию?"):
            games.cancel_game(self.app.conn, self.app.user, game_id)
            self.clear_form()

    def on_delete(self):
        """Удаляет выбранную отменённую сессию после подтверждения."""
        game_id = self.selected_game()
        question = "Удалить сессию вместе с заявками и заметкой?"
        if messagebox.askyesno("Удаление сессии", question):
            games.delete_game(self.app.conn, self.app.user, game_id)
            self.clear_form()


class SignupsTab(Tab):
    """Вкладка «Заявки»: подтверждение и отклонение (макет 04)."""

    STATUS_FILTER = ["Все статусы"] + list(signups.STATUS_NAMES.values())

    def __init__(self, parent, app):
        """Создаёт выбор сессии, таблицу заявок и карточку персонажа.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        self.game_ids = {}  # подпись в списке -> id сессии
        self.rows = {}  # id заявки -> строка заявки

        info = card(self, "Карточка персонажа", "только чтение")
        info.master.pack(side="right", fill="y", padx=px((16, 0)))
        self.char_name = ttk.Label(info, font=("Georgia", 15, "bold"), width=19)
        self.char_name.pack(anchor="w")
        self.char_owner = ttk.Label(info, style="Muted.TLabel")
        self.char_owner.pack(anchor="w", pady=px((0, 10)))
        grid = ttk.Frame(info)
        grid.pack(fill="x")
        self.char_fields = {}
        for row, name in enumerate(("Раса", "Класс", "Уровень")):
            ttk.Label(grid, text=name, style="Muted.TLabel").grid(
                row=row, column=0, sticky="w", pady=px(2)
            )
            self.char_fields[name] = ttk.Label(grid)
            self.char_fields[name].grid(row=row, column=1, sticky="w", padx=px((40, 0)))
        ttk.Label(info, text="ПРЕДЫСТОРИЯ", style="Small.TLabel").pack(
            anchor="w", pady=px((14, 4))
        )
        self.char_story = ttk.Label(info, wraplength=px(230), justify="left")
        self.char_story.pack(anchor="w")

        top = ttk.Frame(self, style="Page.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Сессия:", style="Page.TLabel").pack(side="left")
        self.game_box = ttk.Combobox(top, state="readonly", width=36)
        self.game_box.pack(side="left", padx=px(6))
        self.game_box.bind("<<ComboboxSelected>>", lambda e: self.load_signups())
        self.status_box = ttk.Combobox(
            top, values=self.STATUS_FILTER, state="readonly", width=17
        )
        self.status_box.set("Все статусы")
        self.status_box.pack(side="left", padx=px(6))
        self.status_box.bind("<<ComboboxSelected>>", lambda e: self.load_signups())
        self.seats = tk.Frame(top, bg=PAGE)
        self.seats.pack(side="right")

        self.table = RowTable(
            self,
            [
                ("Персонаж", 179, True),
                ("Игрок", 106, False),
                ("Комментарий", 134, True),
                ("Подана", 95, False),
                ("Статус", 134, False),
                ("Действия", 224, False),
            ],
            on_select=self.on_select,
        )
        self.table.pack(fill="both", expand=True, pady=px((12, 0)))
        self.blocked = Banner(self, fill="x", pady=px((12, 0)))

    def refresh(self):
        """Перечитывает список своих сессий и заявки выбранной сессии."""
        current = self.game_box.get()
        self.game_ids = {
            f"{g['title']}  {to_short(g['scheduled_at'])}": g["id"]
            for g in self.my_games()
        }
        self.game_box.config(values=list(self.game_ids))
        if current not in self.game_ids:
            self.game_box.set(next(iter(self.game_ids), ""))
        self.load_signups()

    def show_character(self, char) -> None:
        """Заполняет карточку персонажа (или очищает, если char = None)."""
        self.char_name.config(text=char["name"] if char else "Выберите заявку")
        self.char_owner.config(text=f"Игрок: {char['owner_name']}" if char else "")
        values = {
            "Раса": char["race"] if char else "",
            "Класс": char["class"] if char else "",
            "Уровень": char["level"] if char else "",
        }
        for name, value in values.items():
            self.char_fields[name].config(text=value or "—")
        self.char_story.config(text=(char["backstory"] if char else "") or "—")

    def show_seats(self, game) -> None:
        """Показывает свободные места квадратиками: «■■■□□ Свободно: 2 из 5»."""
        for child in self.seats.winfo_children():
            child.destroy()
        if game is None:
            ttk.Label(
                self.seats, text="Нет предстоящих сессий", style="Page.TLabel"
            ).pack()
            return
        free = free_of(game)
        if game["max_players"] <= 8:
            squares = "■" * game["confirmed"] + "□" * free
            tk.Label(
                self.seats, text=squares, fg=GREEN_TEXT, bg=PAGE, font=("Segoe UI", 12)
            ).pack(side="left", padx=px((0, 10)))
        ttk.Label(
            self.seats,
            text=f"Свободно: {free} из {game['max_players']}",
            style="PageGreen.TLabel",
        ).pack(side="left")

    def load_signups(self):
        """Показывает заявки выбранной сессии."""
        self.show_character(None)
        self.blocked.hide()
        self.table.clear(
            "Заявок на эту сессию пока нет.\nИгроки увидят её на витрине сессий."
        )
        game_id = self.game_ids.get(self.game_box.get())
        if game_id is None:
            self.show_seats(None)
            return
        game = games.get_game(self.app.conn, game_id)
        free = free_of(game)
        self.show_seats(game)

        status_filter = self.status_box.get()
        self.rows = {}
        has_pending = False
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
                            "Small.Accent.TButton",
                            lambda i=row["id"]: self.on_confirm(i),
                            free > 0,
                        ),
                        (
                            "Отклонить",
                            "Small.Danger.TButton",
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
                        + ([("muted", row["reason"])] if row["reason"] else []),
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
            self.blocked.show(
                f"Подтвердить заявку нельзя. На «{game['title']}» уже подтверждено "
                f"{game['confirmed']} заявок из {game['max_players']}. Отклоните "
                "заявку или увеличьте лимит мест во вкладке «Расписание»."
            )

    def on_select(self, signup_id):
        """Показывает карточку персонажа из выбранной заявки."""
        char_id = self.rows[signup_id]["character_id"]
        self.show_character(characters.get_character(self.app.conn, char_id))

    def on_confirm(self, signup_id):
        """Подтверждает заявку."""
        signups.confirm_signup(self.app.conn, self.app.user, signup_id)
        self.load_signups()

    def on_reject(self, signup_id):
        """Отклоняет заявку; причину отказа можно указать (её увидит Игрок)."""
        reason = ask_text(self, "Отклонить заявку", "Причина отказа (необязательно)")
        if reason is None:
            return
        signups.reject_signup(self.app.conn, self.app.user, signup_id, reason)
        self.load_signups()


class GameNotesTab(Tab):
    """Вкладка «Сюжетный блокнот»: заметка к выбранной сессии (макет 05)."""

    def __init__(self, parent, app):
        """Создаёт список сессий и редактор заметки.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        self.game_id = None

        self.table = RowTable(self, [("Сессии", 280, True)], on_select=self.on_select)
        self.table.pack(side="left", fill="y")

        right = card(self)
        right.master.pack(side="left", fill="both", expand=True, padx=px((16, 0)))
        head = ttk.Frame(right)
        head.pack(fill="x")
        self.title_label = ttk.Label(
            head, text="Выберите сессию слева", style="Bold.TLabel"
        )
        self.title_label.pack(side="left")
        self.date_label = ttk.Label(head, style="Muted.TLabel")
        self.date_label.pack(side="left", padx=px((6, 0)))
        ttk.Label(head, text="видно только Мастеру", style="Small.TLabel").pack(
            side="right"
        )
        ttk.Frame(right, style="Line.TFrame", height=1).pack(fill="x", pady=px(10))
        self.team = ttk.Frame(right)
        self.team.pack(fill="x", pady=px((0, 10)))
        self.editor = make_text(right, height=14, headings=True)
        self.editor.pack(fill="both", expand=True)
        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=px((10, 0)))
        self.updated = ttk.Label(bottom, style="Small.TLabel")
        self.updated.pack(side="left")
        ttk.Button(
            bottom, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(bottom, text="Отменить правки", command=self.reload).pack(
            side="right", padx=px(6)
        )
        ttk.Button(
            bottom,
            text="Удалить заметку",
            style="Danger.TButton",
            command=self.on_delete,
        ).pack(side="right")

    def refresh(self):
        """Перечитывает список своих предстоящих и прошедших сессий."""
        conn, user = self.app.conn, self.app.user
        self.table.clear("Сессий нет.\nСоздайте сессию во вкладке «Расписание».")
        for game in self.my_games() + self.my_games("CLOSED"):
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

    def on_select(self, game_id):
        """Запоминает выбранную сессию и показывает её заметку (сценарий 11)."""
        self.game_id = game_id
        self.reload()

    def reload(self):
        """Показывает заметку и состав выбранной сессии."""
        if self.game_id is None:
            return
        game = games.get_game(self.app.conn, self.game_id)
        self.title_label.config(text=game["title"])
        self.date_label.config(text=f"· {to_show(game['scheduled_at'])}")
        for child in self.team.winfo_children():
            child.destroy()
        ttk.Label(self.team, text="СОСТАВ", style="Small.TLabel").pack(
            side="left", padx=px((0, 8))
        )
        team = [
            row
            for row in signups.list_for_game(self.app.conn, self.game_id)
            if row["status"] == "CONFIRMED"
        ]
        for row in team:
            text = f"{row['character_name']}  {row['character_class'] or ''} " + str(
                row["character_level"]
            )
            Pill(self.team, text, "chip").pack(side="left", padx=px((0, 6)))
        if not team:
            ttk.Label(self.team, text="пока никого", style="Muted.TLabel").pack(
                side="left"
            )
        note = notes.get_game_note(self.app.conn, self.app.user, self.game_id)
        set_text(self.editor, note["content"] if note else "")
        changed = to_show(note["updated_at"]) if note else "—"
        self.updated.config(text=f"Изменено автоматически: {changed}")

    def on_save(self):
        """Сохраняет заметку выбранной сессии."""
        updated_at = notes.save_game_note(
            self.app.conn, self.app.user, self.game_id, get_text(self.editor)
        )
        self.updated.config(text=f"Изменено автоматически: {to_show(updated_at)}")
        self.refresh()

    def on_delete(self):
        """Удаляет заметку выбранной сессии после подтверждения."""
        if self.game_id is None:
            raise ValidationError("Сессия", "Выберите сессию в списке слева.")
        if messagebox.askyesno("Сюжетный блокнот", "Удалить заметку к этой сессии?"):
            notes.delete_game_note(self.app.conn, self.app.user, self.game_id)
            set_text(self.editor, "")
            self.updated.config(text="Изменено автоматически: —")
            self.refresh()


class WorldTab(Tab):
    """Вкладка «База мира»: лор, NPC и локации (макет 06)."""

    FILTERS = [("Все", ""), ("Лор", "LORE"), ("NPC", "NPC"), ("Локации", "LOCATION")]

    def __init__(self, parent, app):
        """Создаёт фильтры, список записей и форму записи.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        self.note_id = None

        top = ttk.Frame(self, style="Page.TFrame")
        top.pack(fill="x")
        self.category_filter = tk.StringVar(value="")
        self.filter_bar = segmented(
            top, self.FILTERS, self.category_filter, self.refresh
        )
        self.filter_bar.pack(side="left")
        ttk.Label(top, text="   ⌕ Поиск по заголовку", style="Page.TLabel").pack(
            side="left"
        )
        self.search = ttk.Entry(top, width=28)
        self.search.pack(side="left", padx=px(6))
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        ttk.Button(
            top, text="+ Новая запись", style="Accent.TButton", command=self.clear_form
        ).pack(side="right")

        body = ttk.Frame(self, style="Page.TFrame")
        body.pack(fill="both", expand=True, pady=px((12, 0)))
        self.table = RowTable(
            body, [("Записи", 314, True)], header=False, on_select=self.on_select
        )
        self.table.pack(side="left", fill="y")

        form = card(body)
        form.master.pack(side="left", fill="both", expand=True, padx=px((16, 0)))
        row = ttk.Frame(form)
        row.pack(fill="x")
        title_box, category_box = ttk.Frame(row), ttk.Frame(row)
        title_box.pack(side="left", fill="x", expand=True, padx=px((0, 12)))
        category_box.pack(side="left")
        field(title_box, "Заголовок *")
        self.title_entry = ttk.Entry(title_box)
        self.title_entry.pack(fill="x")
        field(category_box, "Категория *")
        self.category = ttk.Combobox(
            category_box, values=list(notes.CATEGORY_NAMES.values()), state="readonly"
        )
        self.category.pack(ipady=px(2))
        self.content = make_text(form, height=12, headings=True)
        self.content.pack(fill="both", expand=True, pady=px((12, 0)))
        bottom = ttk.Frame(form)
        bottom.pack(fill="x", pady=px((10, 0)))
        self.updated = ttk.Label(bottom, style="Small.TLabel")
        self.updated.pack(side="left")
        ttk.Button(
            bottom, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(
            bottom, text="Удалить", style="Danger.TButton", command=self.on_delete
        ).pack(side="right", padx=px(6))
        self.error = Banner(form, fill="x", pady=px((10, 0)), before=bottom)
        self.clear_form()

    def refresh(self):
        """Перечитывает свои записи с учётом фильтра и поиска."""
        conn, user = self.app.conn, self.app.user
        everything = notes.list_world_notes(conn, user)
        # Подписи фильтров с количеством записей: «NPC · 6».
        buttons = [
            w
            for w in self.filter_bar.winfo_children()
            if isinstance(w, ttk.Radiobutton)
        ]
        for button, (name, code) in zip(buttons, self.FILTERS):
            count = sum(1 for n in everything if not code or n["category"] == code)
            button.config(text=f"{name} · {count}")
        self.table.clear("Записей нет.\nНажмите «+ Новая запись».")
        rows = notes.list_world_notes(
            conn, user, self.category_filter.get() or None, self.search.get()
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
        self.title_entry.delete(0, "end")
        self.category.set("")
        set_text(self.content, "")
        self.updated.config(text="Новая запись")
        self.error.hide()
        self.refresh()
        self.title_entry.focus()

    def on_select(self, note_id):
        """Загружает выбранную запись в форму."""
        row = notes.get_world_note(self.app.conn, self.app.user, note_id)
        self.note_id = note_id
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, row["title"])
        self.category.set(notes.CATEGORY_NAMES[row["category"]])
        set_text(self.content, row["content"])
        self.updated.config(text=f"Изменено: {to_show(row['updated_at'])}")
        self.error.hide()

    def on_save(self):
        """Сохраняет запись из формы; ошибку показывает в форме."""
        codes = {name: code for code, name in notes.CATEGORY_NAMES.items()}
        try:
            self.note_id = notes.save_world_note(
                self.app.conn,
                self.app.user,
                codes.get(self.category.get()),
                self.title_entry.get(),
                get_text(self.content),
                self.note_id,
            )
        except ValidationError as error:
            self.error.show(error.message)
            return
        self.error.hide()
        self.refresh()

    def on_delete(self):
        """Удаляет выбранную запись после подтверждения."""
        if self.note_id is None:
            raise ValidationError("Запись", "Выберите запись в списке.")
        if messagebox.askyesno("База мира", "Удалить эту запись?"):
            notes.delete_world_note(self.app.conn, self.app.user, self.note_id)
            self.clear_form()
