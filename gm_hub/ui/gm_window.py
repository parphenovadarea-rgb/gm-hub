"""Окно Мастера: вкладки «Расписание», «Заявки», «Сюжетный блокнот», «База мира».

Макеты 03–06. Окно только показывает данные и вызывает функции из logic.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.config import to_short, to_show
from gm_hub.logic import characters, games, notes, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    Banner,
    MainFrame,
    card,
    clear_table,
    field,
    get_text,
    is_soon,
    make_table,
    make_text,
    seats_bar,
    segmented,
    selected_id,
    set_text,
)


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
            [
                ("Расписание", ScheduleTab),
                ("Заявки", SignupsTab),
                ("Сюжетный блокнот", GameNotesTab),
                ("База мира", WorldTab),
            ],
        )

    def on_tab_shown(self):
        """Обновляет счётчик новых заявок на вкладке «Заявки»."""
        pending = sum(game["pending"] for game in games.list_games(self.app.conn))
        self.set_tab_title(1, f"Заявки ({pending})" if pending else "Заявки")


class ScheduleTab(ttk.Frame):
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
        super().__init__(parent, padding=16)
        self.app = app
        self.game_id = None  # id сессии в форме, None — новая сессия

        form = card(self, "Новая сессия")
        form.master.pack(side="right", fill="y", padx=(16, 0))
        self.form = form

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.period = tk.StringVar(value="PLANNED")
        segmented(top, self.PERIODS, self.period, self.refresh).pack(side="left")
        ttk.Button(
            top, text="Удалить сессию", style="Danger.TButton", command=self.on_delete
        ).pack(side="right")
        ttk.Button(
            top, text="Отменить сессию", style="Danger.TButton", command=self.on_cancel
        ).pack(side="right", padx=6)
        ttk.Button(
            top, text="+ Новая сессия", style="Accent.TButton", command=self.clear_form
        ).pack(side="right")

        self.table = make_table(
            self,
            [
                ("Название", 330),
                ("Дата и время", 140),
                ("Места", 150),
                ("Новых заявок", 110),
                ("Статус", 120),
            ],
            tall=True,
        )
        self.table.master.pack(fill="both", expand=True, pady=12)
        self.table.bind("<<TreeviewSelect>>", self.on_select)
        self.summary = ttk.Label(self, style="Muted.TLabel")
        self.summary.pack(anchor="w")

        field(form, "Название *")
        self.title_entry = ttk.Entry(form, width=34)
        self.title_entry.pack(fill="x", ipady=2)
        field(form, "Описание для игроков")
        self.description = make_text(form, height=3)
        self.description.pack(fill="x")
        row = ttk.Frame(form)
        row.pack(fill="x")
        date_box, time_box = ttk.Frame(row), ttk.Frame(row)
        date_box.pack(side="left", fill="x", expand=True, padx=(0, 8))
        time_box.pack(side="left", fill="x", expand=True)
        field(date_box, "Дата * (ДД.ММ.ГГГГ)")
        self.date_entry = ttk.Entry(date_box, width=14)
        self.date_entry.pack(fill="x", ipady=2)
        field(time_box, "Время * (ЧЧ:ММ)")
        self.time_entry = ttk.Entry(time_box, width=8)
        self.time_entry.pack(fill="x", ipady=2)
        field(form, "Лимит мест *")
        self.max_players = ttk.Spinbox(form, from_=1, to=50, width=8)
        self.max_players.pack(anchor="w")
        ttk.Label(form, text="Целое число больше нуля", style="Small.TLabel").pack(
            anchor="w"
        )
        self.save_button = ttk.Button(
            form, text="Опубликовать", style="Accent.TButton", command=self.on_save
        )
        self.save_button.pack(fill="x", pady=(14, 0), ipady=3)
        self.error = Banner(form, fill="x", pady=(10, 0), before=self.save_button)
        self.clear_form()

    def refresh(self):
        """Перечитывает сессии из БД."""
        clear_table(self.table)
        for game in games.list_games(self.app.conn, self.period.get()):
            tags = ("soon",) if is_soon(game["scheduled_at"]) else ()
            self.table.insert(
                "",
                "end",
                iid=game["id"],
                tags=tags,
                values=(
                    f"{game['title']}\n{game['description'] or ''}",
                    to_show(game["scheduled_at"]),
                    seats_bar(free_of(game), game["max_players"]),
                    game["pending"],
                    games.STATUS_NAMES[game["status"]],
                ),
            )
        planned = games.list_games(self.app.conn)
        free = sum(free_of(game) for game in planned)
        pending = sum(game["pending"] for game in planned)
        self.summary.config(
            text=f"Предстоящих: {len(planned)}     Свободных мест всего: {free}     "
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
        self.table.selection_remove(self.table.selection())

    def on_select(self, event=None):
        """Загружает выбранную сессию в форму для изменения."""
        game_id = selected_id(self.table)
        if game_id is None:
            return
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
        self.refresh()

    def selected_game(self) -> int:
        """Возвращает id выбранной сессии или сообщает, что её нет."""
        game_id = selected_id(self.table)
        if game_id is None:
            raise ValidationError("Сессия", "Выберите сессию в таблице.")
        return game_id

    def on_cancel(self):
        """Отменяет выбранную сессию после подтверждения."""
        game_id = self.selected_game()
        if messagebox.askyesno("Отмена сессии", "Отменить выбранную сессию?"):
            games.cancel_game(self.app.conn, self.app.user, game_id)
            self.clear_form()
            self.refresh()

    def on_delete(self):
        """Удаляет выбранную отменённую сессию после подтверждения."""
        game_id = self.selected_game()
        question = "Удалить сессию вместе с заявками и заметкой?"
        if messagebox.askyesno("Удаление сессии", question):
            games.delete_game(self.app.conn, self.app.user, game_id)
            self.clear_form()
            self.refresh()


class SignupsTab(ttk.Frame):
    """Вкладка «Заявки»: подтверждение и отклонение (макет 04)."""

    STATUS_FILTER = ["Все статусы"] + list(signups.STATUS_NAMES.values())

    def __init__(self, parent, app):
        """Создаёт выбор сессии, таблицу заявок и карточку персонажа.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=16)
        self.app = app
        self.game_ids = {}  # подпись в списке -> id сессии
        self.rows = {}  # id заявки -> строка заявки

        info = card(self, "Карточка персонажа", "только чтение")
        info.master.pack(side="right", fill="y", padx=(16, 0))
        self.char_name = ttk.Label(info, font=("Georgia", 16, "bold"), width=28)
        self.char_name.pack(anchor="w")
        self.char_owner = ttk.Label(info, style="Muted.TLabel")
        self.char_owner.pack(anchor="w", pady=(0, 10))
        grid = ttk.Frame(info)
        grid.pack(fill="x")
        self.char_fields = {}
        for row, name in enumerate(("Раса", "Класс", "Уровень")):
            ttk.Label(grid, text=name, style="Muted.TLabel").grid(
                row=row, column=0, sticky="w", pady=2
            )
            self.char_fields[name] = ttk.Label(grid)
            self.char_fields[name].grid(row=row, column=1, sticky="w", padx=(30, 0))
        ttk.Label(info, text="ПРЕДЫСТОРИЯ", style="Small.TLabel").pack(
            anchor="w", pady=(12, 4)
        )
        self.char_story = ttk.Label(info, wraplength=300, justify="left")
        self.char_story.pack(anchor="w")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Сессия:", style="Muted.TLabel").pack(side="left")
        self.game_box = ttk.Combobox(top, state="readonly", width=38)
        self.game_box.pack(side="left", padx=6)
        self.game_box.bind("<<ComboboxSelected>>", lambda e: self.load_signups())
        self.status_box = ttk.Combobox(
            top, values=self.STATUS_FILTER, state="readonly", width=18
        )
        self.status_box.set("Все статусы")
        self.status_box.pack(side="left", padx=6)
        self.status_box.bind("<<ComboboxSelected>>", lambda e: self.load_signups())
        self.seats = ttk.Label(top, style="Green.TLabel")
        self.seats.pack(side="right")

        self.table = make_table(
            self,
            [
                ("Персонаж", 160),
                ("Игрок", 140),
                ("Комментарий", 180),
                ("Подана", 100),
                ("Статус", 125),
                ("Решение", 100),
            ],
        )
        self.table.master.pack(fill="both", expand=True, pady=12)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x")
        self.confirm_button = ttk.Button(
            buttons,
            text="✓ Подтвердить",
            style="Accent.TButton",
            command=self.on_confirm,
        )
        self.confirm_button.pack(side="left")
        ttk.Button(
            buttons, text="Отклонить", style="Danger.TButton", command=self.on_reject
        ).pack(side="left", padx=6)
        self.blocked = Banner(self, fill="x", pady=(10, 0))

    def refresh(self):
        """Перечитывает список сессий и заявки выбранной сессии."""
        current = self.game_box.get()
        self.game_ids = {
            f"{g['title']} · {to_show(g['scheduled_at'])}": g["id"]
            for g in games.list_games(self.app.conn)
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

    def load_signups(self):
        """Показывает заявки выбранной сессии."""
        clear_table(self.table)
        self.show_character(None)
        self.blocked.hide()
        game_id = self.game_ids.get(self.game_box.get())
        if game_id is None:
            self.seats.config(text="Нет предстоящих сессий")
            return
        game = games.get_game(self.app.conn, game_id)
        free = free_of(game)
        bar = "■" * game["confirmed"] + "□" * free if game["max_players"] <= 8 else ""
        self.seats.config(text=f"{bar}  Свободно: {free} из {game['max_players']}")
        # Автоматическая блокировка подтверждения при достижении лимита (п. 4.2.3).
        if free <= 0:
            self.confirm_button.state(["disabled"])
            self.blocked.show(
                f"Подтвердить заявку нельзя. На «{game['title']}» уже подтверждено "
                f"{game['confirmed']} заявок из {game['max_players']}. Отклоните "
                "заявку или увеличьте лимит мест во вкладке «Расписание»."
            )
        else:
            self.confirm_button.state(["!disabled"])

        status_filter = self.status_box.get()
        self.rows = {}
        for row in signups.list_for_game(self.app.conn, game_id):
            status = signups.STATUS_NAMES[row["status"]]
            if status_filter != "Все статусы" and status != status_filter:
                continue
            self.rows[row["id"]] = row
            self.table.insert(
                "",
                "end",
                iid=row["id"],
                tags=(row["status"],),
                values=(
                    f"{row['character_name']} · {row['character_class'] or ''} "
                    f"{row['character_level']}",
                    row["player_name"],
                    row["comment"] or "—",
                    to_short(row["created_at"]),
                    status,
                    to_short(row["decided_at"]),
                ),
            )

    def on_select(self, event=None):
        """Показывает карточку персонажа из выбранной заявки."""
        signup_id = selected_id(self.table)
        if signup_id is not None:
            char_id = self.rows[signup_id]["character_id"]
            self.show_character(characters.get_character(self.app.conn, char_id))

    def selected_signup(self) -> int:
        """Возвращает id выбранной заявки или сообщает, что её нет."""
        signup_id = selected_id(self.table)
        if signup_id is None:
            raise ValidationError("Заявка", "Выберите заявку в таблице.")
        return signup_id

    def on_confirm(self):
        """Подтверждает выбранную заявку."""
        signups.confirm_signup(self.app.conn, self.app.user, self.selected_signup())
        self.load_signups()

    def on_reject(self):
        """Отклоняет выбранную заявку."""
        signups.reject_signup(self.app.conn, self.app.user, self.selected_signup())
        self.load_signups()


class GameNotesTab(ttk.Frame):
    """Вкладка «Сюжетный блокнот»: заметка к выбранной сессии (макет 05)."""

    def __init__(self, parent, app):
        """Создаёт список сессий и редактор заметки.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=16)
        self.app = app
        self.game_id = None

        self.table = make_table(self, [("Сессии", 260)], tall=True)
        self.table.master.pack(side="left", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        right = card(self)
        right.master.pack(side="left", fill="both", expand=True, padx=(16, 0))
        head = ttk.Frame(right)
        head.pack(fill="x")
        self.title_label = ttk.Label(
            head, text="Выберите сессию слева", font=("Georgia", 14, "bold")
        )
        self.title_label.pack(side="left")
        ttk.Label(head, text="видно только Мастеру", style="Small.TLabel").pack(
            side="right"
        )
        self.team = ttk.Label(right, style="Muted.TLabel", wraplength=700)
        self.team.pack(anchor="w", pady=(8, 8))
        self.editor = make_text(right, height=14)
        self.editor.pack(fill="both", expand=True)
        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(10, 0))
        self.updated = ttk.Label(bottom, style="Small.TLabel")
        self.updated.pack(side="left")
        ttk.Button(
            bottom, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(bottom, text="Отменить правки", command=self.on_select).pack(
            side="right", padx=6
        )
        ttk.Button(
            bottom,
            text="Удалить заметку",
            style="Danger.TButton",
            command=self.on_delete,
        ).pack(side="right")

    def refresh(self):
        """Перечитывает список предстоящих и прошедших сессий."""
        conn, user = self.app.conn, self.app.user
        clear_table(self.table)
        for game in games.list_games(conn) + games.list_games(conn, "CLOSED"):
            note = notes.get_game_note(conn, user, game["id"])
            if game["status"] == "CLOSED":
                state = "прошла"
            else:
                state = "заметка есть" if note and note["content"] else "пусто"
            when = to_show(game["scheduled_at"])
            self.table.insert(
                "",
                "end",
                iid=game["id"],
                values=(f"{game['title']}\n{when} · {state}",),
            )
        if self.game_id and self.table.exists(self.game_id):
            self.table.selection_set(self.game_id)

    def on_select(self, event=None):
        """Показывает заметку и состав выбранной сессии (сценарий 11)."""
        game_id = selected_id(self.table)
        if game_id is None:
            return
        self.game_id = game_id
        game = games.get_game(self.app.conn, game_id)
        self.title_label.config(
            text=f"{game['title']} · {to_show(game['scheduled_at'])}"
        )
        team = [
            f"{row['character_name']} ({row['character_class'] or '—'} "
            f"{row['character_level']})"
            for row in signups.list_for_game(self.app.conn, game_id)
            if row["status"] == "CONFIRMED"
        ]
        self.team.config(text="СОСТАВ:  " + ("   ".join(team) or "пока никого"))
        note = notes.get_game_note(self.app.conn, self.app.user, game_id)
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


class WorldTab(ttk.Frame):
    """Вкладка «База мира»: лор, NPC и локации (макет 06)."""

    FILTERS = [("Все", ""), ("Лор", "LORE"), ("NPC", "NPC"), ("Локации", "LOCATION")]

    def __init__(self, parent, app):
        """Создаёт фильтры, список записей и форму записи.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=16)
        self.app = app
        self.note_id = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.category_filter = tk.StringVar(value="")
        self.filter_bar = segmented(
            top, self.FILTERS, self.category_filter, self.refresh
        )
        self.filter_bar.pack(side="left")
        ttk.Label(top, text="   ⌕", style="Muted.TLabel").pack(side="left")
        self.search = ttk.Entry(top, width=30)
        self.search.pack(side="left", padx=6, ipady=2)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        ttk.Button(
            top, text="+ Новая запись", style="Accent.TButton", command=self.clear_form
        ).pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(12, 0))
        self.table = make_table(body, [("Записи", 300)], tall=True)
        self.table.master.pack(side="left", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = card(body)
        form.master.pack(side="left", fill="both", expand=True, padx=(16, 0))
        row = ttk.Frame(form)
        row.pack(fill="x")
        title_box, category_box = ttk.Frame(row), ttk.Frame(row)
        title_box.pack(side="left", fill="x", expand=True, padx=(0, 12))
        category_box.pack(side="left")
        field(title_box, "Заголовок *")
        self.title_entry = ttk.Entry(title_box)
        self.title_entry.pack(fill="x", ipady=2)
        field(category_box, "Категория *")
        self.category = ttk.Combobox(
            category_box, values=list(notes.CATEGORY_NAMES.values()), state="readonly"
        )
        self.category.pack(ipady=2)
        self.content = make_text(form, height=12)
        self.content.pack(fill="both", expand=True, pady=(12, 0))
        bottom = ttk.Frame(form)
        bottom.pack(fill="x", pady=(10, 0))
        self.updated = ttk.Label(bottom, style="Small.TLabel")
        self.updated.pack(side="left")
        ttk.Button(
            bottom, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(
            bottom, text="Удалить", style="Danger.TButton", command=self.on_delete
        ).pack(side="right", padx=6)
        self.error = Banner(form, fill="x", pady=(10, 0), before=bottom)

    def refresh(self):
        """Перечитывает записи с учётом фильтра и поиска."""
        conn, user = self.app.conn, self.app.user
        everything = notes.list_world_notes(conn, user)
        # Подписи фильтров с количеством записей: «NPC · 6».
        for button, (name, code) in zip(self.filter_bar.winfo_children(), self.FILTERS):
            count = sum(1 for n in everything if not code or n["category"] == code)
            button.config(text=f"{name} · {count}")
        clear_table(self.table)
        rows = notes.list_world_notes(
            conn, user, self.category_filter.get() or None, self.search.get()
        )
        for row in rows:
            category = notes.CATEGORY_NAMES[row["category"]]
            self.table.insert(
                "", "end", iid=row["id"], values=(f"{row['title']}\n{category}",)
            )

    def clear_form(self):
        """Очищает форму для новой записи."""
        self.note_id = None
        self.title_entry.delete(0, "end")
        self.category.set("")
        set_text(self.content, "")
        self.updated.config(text="Новая запись")
        self.error.hide()
        self.title_entry.focus()

    def on_select(self, event=None):
        """Загружает выбранную запись в форму."""
        note_id = selected_id(self.table)
        if note_id is None:
            return
        row = next(
            r
            for r in notes.list_world_notes(self.app.conn, self.app.user)
            if r["id"] == note_id
        )
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
        if self.table.exists(self.note_id):
            self.table.selection_set(self.note_id)

    def on_delete(self):
        """Удаляет выбранную запись после подтверждения."""
        if self.note_id is None:
            raise ValidationError("Запись", "Выберите запись в списке.")
        if messagebox.askyesno("База мира", "Удалить эту запись?"):
            notes.delete_world_note(self.app.conn, self.app.user, self.note_id)
            self.clear_form()
            self.refresh()
