"""Окно Мастера: вкладки «Расписание», «Заявки», «Сюжетный блокнот», «База мира».

Макеты 03–06. Окно только показывает данные и вызывает функции из logic.
"""

from tkinter import messagebox, ttk

from gm_hub.config import to_show
from gm_hub.logic import characters, games, notes, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    FONT_BOLD,
    clear_table,
    get_text,
    is_soon,
    make_header,
    make_table,
    make_text,
    selected_id,
    set_text,
)

PERIODS = {"Предстоящие": "PLANNED", "Прошедшие": "CLOSED", "Отменённые": "CANCELLED"}


def seats_text(game) -> str:
    """Возвращает подпись свободных мест, например «3 из 4» или «мест нет».

    Args:
        game: Строка сессии с полями max_players и confirmed.

    Returns:
        Текст для таблицы.
    """
    free = games.free_seats(game["max_players"], game["confirmed"])
    return f"{free} из {game['max_players']}" if free > 0 else "мест нет"


class GMFrame(ttk.Frame):
    """Главное окно Мастера с вкладками."""

    def __init__(self, app):
        """Создаёт шапку и вкладки.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(app)
        self.app = app
        make_header(self, app, "Кабинет Мастера").pack(fill="x")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.schedule = ScheduleTab(self.tabs, app)
        self.signups = SignupsTab(self.tabs, app)
        self.tabs.add(self.schedule, text="Расписание")
        self.tabs.add(self.signups, text="Заявки")
        self.tabs.add(GameNotesTab(self.tabs, app), text="Сюжетный блокнот")
        self.tabs.add(WorldTab(self.tabs, app), text="База мира")
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.on_tab_changed()

    def on_tab_changed(self, event=None):
        """Обновляет открытую вкладку и счётчик новых заявок."""
        self.nametowidget(self.tabs.select()).refresh()
        pending = sum(game["pending"] for game in games.list_games(self.app.conn))
        title = f"Заявки ({pending})" if pending else "Заявки"
        self.tabs.tab(self.signups, text=title)


class ScheduleTab(ttk.Frame):
    """Вкладка «Расписание»: список сессий и форма сессии (макет 03)."""

    def __init__(self, parent, app):
        """Создаёт таблицу сессий и форму.

        Args:
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        self.game_id = None  # id сессии в форме, None — новая сессия

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.period = ttk.Combobox(top, values=list(PERIODS), state="readonly")
        self.period.set("Предстоящие")
        self.period.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.period.pack(side="left")
        ttk.Button(top, text="Отменить сессию", command=self.on_cancel).pack(
            side="right"
        )
        ttk.Button(
            top, text="+ Новая сессия", style="Accent.TButton", command=self.clear_form
        ).pack(side="right", padx=6)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)
        self.table = make_table(
            body,
            [
                ("Название", 200),
                ("Описание", 220),
                ("Дата и время", 120),
                ("Места", 80),
                ("Новых заявок", 100),
                ("Статус", 110),
            ],
        )
        self.table.master.pack(side="left", fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(body, text="Сессия", padding=10)
        form.pack(side="right", fill="y", padx=(10, 0))
        self.form_title = ttk.Label(form, text="Новая сессия", font=FONT_BOLD)
        self.form_title.pack(anchor="w", pady=(0, 6))
        ttk.Label(form, text="Название *").pack(anchor="w")
        self.title_entry = ttk.Entry(form, width=36)
        self.title_entry.pack(fill="x", pady=(0, 6))
        ttk.Label(form, text="Описание для игроков").pack(anchor="w")
        self.description = make_text(form, height=4)
        self.description.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(form)
        row.pack(fill="x")
        ttk.Label(row, text="Дата * (ДД.ММ.ГГГГ)").grid(row=0, column=0, sticky="w")
        ttk.Label(row, text="Время * (ЧЧ:ММ)").grid(row=0, column=1, sticky="w")
        self.date_entry = ttk.Entry(row, width=14)
        self.date_entry.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.time_entry = ttk.Entry(row, width=8)
        self.time_entry.grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Лимит мест * (целое число больше нуля)").pack(
            anchor="w", pady=(6, 0)
        )
        self.max_players = ttk.Spinbox(form, from_=1, to=50, width=6)
        self.max_players.pack(anchor="w")
        ttk.Button(
            form, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(fill="x", pady=(12, 0))

        self.summary = ttk.Label(self, style="Muted.TLabel")
        self.summary.pack(anchor="w")
        self.clear_form()

    def refresh(self):
        """Перечитывает сессии из БД."""
        clear_table(self.table)
        for game in games.list_games(self.app.conn, PERIODS[self.period.get()]):
            tags = ("soon",) if is_soon(game["scheduled_at"]) else ()
            self.table.insert(
                "",
                "end",
                iid=game["id"],
                tags=tags,
                values=(
                    game["title"],
                    game["description"],
                    to_show(game["scheduled_at"]),
                    seats_text(game),
                    game["pending"],
                    games.STATUS_NAMES[game["status"]],
                ),
            )
        planned = games.list_games(self.app.conn)
        free = sum(games.free_seats(g["max_players"], g["confirmed"]) for g in planned)
        pending = sum(g["pending"] for g in planned)
        self.summary.config(
            text=f"Предстоящих: {len(planned)}    Свободных мест всего: {free}    "
            f"Заявок ждут решения: {pending}"
        )

    def clear_form(self):
        """Очищает форму для новой сессии."""
        self.game_id = None
        self.form_title.config(text="Новая сессия")
        self.title_entry.delete(0, "end")
        set_text(self.description, "")
        self.date_entry.delete(0, "end")
        self.time_entry.delete(0, "end")
        self.max_players.set(4)
        self.table.selection_remove(self.table.selection())

    def on_select(self, event=None):
        """Загружает выбранную сессию в форму для изменения."""
        game_id = selected_id(self.table)
        if game_id is None:
            return
        game = games.get_game(self.app.conn, game_id)
        self.game_id = game_id
        self.form_title.config(text="Изменение сессии")
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, game["title"])
        set_text(self.description, game["description"])
        when = to_show(game["scheduled_at"])
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, when[:10])
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, when[11:])
        self.max_players.set(game["max_players"])

    def on_save(self):
        """Сохраняет сессию из формы."""
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
        messagebox.showinfo("Расписание", "Сессия сохранена и видна в витрине.")
        self.clear_form()
        self.refresh()

    def on_cancel(self):
        """Отменяет выбранную сессию после подтверждения."""
        game_id = selected_id(self.table)
        if game_id is None:
            raise ValidationError("Сессия", "Выберите сессию в таблице.")
        if messagebox.askyesno("Отмена сессии", "Отменить выбранную сессию?"):
            games.cancel_game(self.app.conn, self.app.user, game_id)
            self.clear_form()
            self.refresh()


class SignupsTab(ttk.Frame):
    """Вкладка «Заявки»: подтверждение и отклонение (макет 04)."""

    STATUS_FILTER = ["Все статусы"] + list(signups.STATUS_NAMES.values())

    def __init__(self, parent, app):
        """Создаёт выбор сессии, таблицу заявок и карточку персонажа.

        Args:
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        self.game_ids = {}  # подпись в списке -> id сессии
        self.rows = {}  # id заявки -> строка заявки

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Сессия:").pack(side="left")
        self.game_box = ttk.Combobox(top, state="readonly", width=45)
        self.game_box.pack(side="left", padx=6)
        self.game_box.bind("<<ComboboxSelected>>", lambda e: self.load_signups())
        self.status_box = ttk.Combobox(top, values=self.STATUS_FILTER, state="readonly")
        self.status_box.set("Все статусы")
        self.status_box.pack(side="left", padx=6)
        self.status_box.bind("<<ComboboxSelected>>", lambda e: self.load_signups())
        self.seats = ttk.Label(top, font=FONT_BOLD)
        self.seats.pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        self.table = make_table(
            left,
            [
                ("Персонаж", 150),
                ("Игрок", 140),
                ("Комментарий", 190),
                ("Подана", 120),
                ("Статус", 120),
                ("Решение", 120),
            ],
        )
        self.table.master.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(
            buttons,
            text="✓ Подтвердить",
            style="Accent.TButton",
            command=self.on_confirm,
        ).pack(side="left")
        ttk.Button(buttons, text="Отклонить", command=self.on_reject).pack(
            side="left", padx=6
        )

        card = ttk.LabelFrame(
            body, text="Карточка персонажа (только чтение)", padding=10
        )
        card.pack(side="right", fill="y", padx=(10, 0))
        self.card = ttk.Label(card, width=34, wraplength=260, justify="left")
        self.card.pack(anchor="nw")

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

    def load_signups(self):
        """Показывает заявки выбранной сессии."""
        clear_table(self.table)
        self.card.config(text="Выберите заявку, чтобы увидеть персонажа.")
        game_id = self.game_ids.get(self.game_box.get())
        if game_id is None:
            self.seats.config(text="Нет предстоящих сессий")
            return
        game = games.get_game(self.app.conn, game_id)
        free = games.free_seats(game["max_players"], game["confirmed"])
        text = f"Свободно: {free} из {game['max_players']}"
        if free <= 0:
            text += " — подтверждение заблокировано"
        self.seats.config(text=text, foreground="#a1362c" if free <= 0 else "")

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
                    to_show(row["created_at"]),
                    status,
                    to_show(row["decided_at"]),
                ),
            )

    def on_select(self, event=None):
        """Показывает карточку персонажа из выбранной заявки."""
        signup_id = selected_id(self.table)
        if signup_id is None:
            return
        char = characters.get_character(
            self.app.conn, self.rows[signup_id]["character_id"]
        )
        self.card.config(
            text=f"{char['name']}\nИгрок: {char['owner_name']}\n\n"
            f"Раса: {char['race'] or '—'}\nКласс: {char['class'] or '—'}\n"
            f"Уровень: {char['level']}\n\nПредыстория:\n{char['backstory'] or '—'}"
        )

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
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        self.game_id = None

        self.table = make_table(self, [("Сессия", 190), ("Дата", 120), ("Заметка", 70)])
        self.table.master.pack(side="left", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        right = ttk.Frame(self, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        self.title_label = ttk.Label(
            right, text="Выберите сессию слева", style="Title.TLabel"
        )
        self.title_label.pack(anchor="w")
        ttk.Label(right, text="🔒 видно только Мастеру", style="Muted.TLabel").pack(
            anchor="w"
        )
        self.team = ttk.Label(right, wraplength=600, justify="left")
        self.team.pack(anchor="w", pady=6)
        self.editor = make_text(right, height=16)
        self.editor.pack(fill="both", expand=True)
        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(8, 0))
        self.updated = ttk.Label(bottom, style="Muted.TLabel")
        self.updated.pack(side="left")
        ttk.Button(
            bottom, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(bottom, text="Отменить правки", command=self.on_select).pack(
            side="right", padx=6
        )

    def refresh(self):
        """Перечитывает список предстоящих и прошедших сессий."""
        conn, user = self.app.conn, self.app.user
        clear_table(self.table)
        for game in games.list_games(conn) + games.list_games(conn, "CLOSED"):
            note = notes.get_game_note(conn, user, game["id"])
            has_note = "есть" if note and note["content"] else "пусто"
            self.table.insert(
                "",
                "end",
                iid=game["id"],
                values=(game["title"], to_show(game["scheduled_at"]), has_note),
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
        self.team.config(text="Состав: " + (", ".join(team) or "пока никого"))
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


class WorldTab(ttk.Frame):
    """Вкладка «База мира»: лор, NPC и локации (макет 06)."""

    FILTERS = {"Все": None, "Лор": "LORE", "NPC": "NPC", "Локации": "LOCATION"}

    def __init__(self, parent, app):
        """Создаёт фильтры, список записей и форму записи.

        Args:
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        self.note_id = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.category_filter = ttk.Combobox(
            top, values=list(self.FILTERS), state="readonly", width=12
        )
        self.category_filter.set("Все")
        self.category_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.category_filter.pack(side="left")
        ttk.Label(top, text="   ⌕ Поиск по заголовку:").pack(side="left")
        self.search = ttk.Entry(top, width=30)
        self.search.pack(side="left", padx=6)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        ttk.Button(
            top, text="+ Новая запись", style="Accent.TButton", command=self.clear_form
        ).pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)
        self.table = make_table(body, [("Категория", 90), ("Заголовок", 230)])
        self.table.master.pack(side="left", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.Frame(body, padding=(12, 0, 0, 0))
        form.pack(side="left", fill="both", expand=True)
        ttk.Label(form, text="Заголовок *").pack(anchor="w")
        self.title_entry = ttk.Entry(form)
        self.title_entry.pack(fill="x", pady=(0, 6))
        ttk.Label(form, text="Категория *").pack(anchor="w")
        self.category = ttk.Combobox(
            form, values=list(notes.CATEGORY_NAMES.values()), state="readonly"
        )
        self.category.pack(anchor="w", pady=(0, 6))
        self.content = make_text(form, height=14)
        self.content.pack(fill="both", expand=True)
        bottom = ttk.Frame(form)
        bottom.pack(fill="x", pady=(8, 0))
        self.updated = ttk.Label(bottom, style="Muted.TLabel")
        self.updated.pack(side="left")
        ttk.Button(
            bottom, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(bottom, text="Удалить", command=self.on_delete).pack(
            side="right", padx=6
        )

    def refresh(self):
        """Перечитывает записи с учётом фильтра и поиска."""
        clear_table(self.table)
        rows = notes.list_world_notes(
            self.app.conn,
            self.app.user,
            self.FILTERS[self.category_filter.get()],
            self.search.get(),
        )
        for row in rows:
            self.table.insert(
                "",
                "end",
                iid=row["id"],
                values=(notes.CATEGORY_NAMES[row["category"]], row["title"]),
            )

    def clear_form(self):
        """Очищает форму для новой записи."""
        self.note_id = None
        self.title_entry.delete(0, "end")
        self.category.set("")
        set_text(self.content, "")
        self.updated.config(text="Новая запись")
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

    def on_save(self):
        """Сохраняет запись из формы."""
        codes = {name: code for code, name in notes.CATEGORY_NAMES.items()}
        self.note_id = notes.save_world_note(
            self.app.conn,
            self.app.user,
            codes.get(self.category.get()),
            self.title_entry.get(),
            get_text(self.content),
            self.note_id,
        )
        self.refresh()
        self.table.selection_set(self.note_id)

    def on_delete(self):
        """Удаляет выбранную запись после подтверждения."""
        if self.note_id is None:
            raise ValidationError("Запись", "Выберите запись в списке.")
        if messagebox.askyesno("База мира", "Удалить эту запись?"):
            notes.delete_world_note(self.app.conn, self.app.user, self.note_id)
            self.clear_form()
            self.refresh()
