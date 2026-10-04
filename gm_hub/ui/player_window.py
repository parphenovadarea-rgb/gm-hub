"""Окно Игрока: вкладки «Витрина сессий», «Мои записи», «Мои персонажи».

Макеты 07–09. Вкладок «Сюжетный блокнот» и «База мира» здесь нет
(сценарий 12 п. 6.1 ТЗ).
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.config import now_str, to_show
from gm_hub.logic import characters, games, signups
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


class PlayerFrame(ttk.Frame):
    """Главное окно Игрока с вкладками."""

    def __init__(self, app):
        """Создаёт шапку и вкладки.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(app)
        self.app = app
        make_header(self, app, "Кабинет Игрока").pack(fill="x")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabs.add(ShowcaseTab(self.tabs, app), text="Витрина сессий")
        self.tabs.add(MySignupsTab(self.tabs, app), text="Мои записи")
        self.tabs.add(CharactersTab(self.tabs, app), text="Мои персонажи")
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.on_tab_changed()

    def on_tab_changed(self, event=None):
        """Обновляет открытую вкладку."""
        self.nametowidget(self.tabs.select()).refresh()


class ShowcaseTab(ttk.Frame):
    """Вкладка «Витрина сессий» и запись на игру (макет 07)."""

    def __init__(self, parent, app):
        """Создаёт таблицу сессий и форму заявки.

        Args:
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        self.char_ids = {}  # подпись в списке -> id персонажа

        self.only_free = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self,
            text="Только со свободными местами",
            variable=self.only_free,
            command=self.refresh,
        ).pack(anchor="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)
        self.table = make_table(
            body,
            [
                ("Сессия", 190),
                ("Описание", 220),
                ("Когда", 120),
                ("Свободно", 80),
                ("Мастер", 130),
                ("Моя заявка", 130),
            ],
        )
        self.table.master.pack(side="left", fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(body, text="Запись на сессию", padding=10)
        form.pack(side="right", fill="y", padx=(10, 0))
        self.info = ttk.Label(
            form, text="Выберите сессию в таблице.", width=34, wraplength=260
        )
        self.info.pack(anchor="w", pady=(0, 10))
        ttk.Label(form, text="Персонаж *").pack(anchor="w")
        self.char_box = ttk.Combobox(form, state="readonly", width=34)
        self.char_box.pack(fill="x", pady=(0, 6))
        ttk.Label(form, text="Комментарий Мастеру (необязательно)").pack(anchor="w")
        self.comment = ttk.Entry(form)
        self.comment.pack(fill="x")
        ttk.Button(
            form, text="Отправить заявку", style="Accent.TButton", command=self.on_send
        ).pack(fill="x", pady=(12, 0))

    def refresh(self):
        """Перечитывает витрину и список персонажей."""
        conn, user = self.app.conn, self.app.user
        my_status = {}  # id сессии -> статусы моих заявок
        for row in signups.list_for_player(conn, user):
            status = signups.STATUS_NAMES[row["status"]]
            my_status.setdefault(row["game_id"], []).append(status)

        clear_table(self.table)
        for game in games.list_games(conn):
            free = games.free_seats(game["max_players"], game["confirmed"])
            if self.only_free.get() and free <= 0:
                continue
            self.table.insert(
                "",
                "end",
                iid=game["id"],
                tags=("soon",) if is_soon(game["scheduled_at"]) else (),
                values=(
                    game["title"],
                    game["description"],
                    to_show(game["scheduled_at"]),
                    f"{free} из {game['max_players']}",
                    game["gm_name"],
                    ", ".join(my_status.get(game["id"], [])) or "—",
                ),
            )

        self.char_ids = {}
        for c in characters.list_characters(conn, user):
            label = f"{c['name']} · {c['race'] or '—'} · {c['class'] or '—'}"
            self.char_ids[f"{label} · {c['level']} ур."] = c["id"]
        self.char_box.config(values=list(self.char_ids))
        self.char_box.set("")

    def on_select(self, event=None):
        """Показывает выбранную сессию в форме заявки."""
        game_id = selected_id(self.table)
        if game_id is None:
            return
        game = games.get_game(self.app.conn, game_id)
        free = games.free_seats(game["max_players"], game["confirmed"])
        self.info.config(
            text=f"{game['title']}\n{to_show(game['scheduled_at'])} · "
            f"свободно {free} из {game['max_players']}",
            font=FONT_BOLD,
        )

    def on_send(self):
        """Подаёт заявку выбранным персонажем (сценарии 5–7)."""
        game_id = selected_id(self.table)
        signups.create_signup(
            self.app.conn,
            self.app.user,
            game_id,
            self.char_ids.get(self.char_box.get()),
            self.comment.get(),
        )
        title = games.get_game(self.app.conn, game_id)["title"]
        messagebox.showinfo(
            "Заявка отправлена",
            f"Заявка на «{title}» отправлена. Статус: на рассмотрении.",
        )
        self.comment.delete(0, "end")
        self.refresh()


class MySignupsTab(ttk.Frame):
    """Вкладка «Мои записи»: статусы своих заявок (макет 08)."""

    def __init__(self, parent, app):
        """Создаёт таблицу заявок.

        Args:
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        ttk.Button(self, text="Отозвать заявку", command=self.on_withdraw).pack(
            anchor="e"
        )
        self.table = make_table(
            self,
            [
                ("Сессия", 220),
                ("Когда", 130),
                ("Персонаж", 120),
                ("Мой комментарий", 200),
                ("Статус", 130),
                ("Решение", 120),
            ],
        )
        self.table.master.pack(fill="both", expand=True, pady=8)
        self.summary = ttk.Label(self, style="Muted.TLabel")
        self.summary.pack(anchor="w")

    def refresh(self):
        """Перечитывает заявки текущего Игрока (сценарий 14)."""
        clear_table(self.table)
        rows = signups.list_for_player(self.app.conn, self.app.user)
        for row in rows:
            self.table.insert(
                "",
                "end",
                iid=row["id"],
                tags=(row["status"],),
                values=(
                    row["game_title"],
                    to_show(row["scheduled_at"]),
                    row["character_name"],
                    row["comment"] or "—",
                    signups.STATUS_NAMES[row["status"]],
                    to_show(row["decided_at"]),
                ),
            )
        confirmed = [r for r in rows if r["status"] == "CONFIRMED"]
        pending = [r for r in rows if r["status"] == "PENDING"]
        upcoming = [r for r in confirmed if r["scheduled_at"] >= now_str()]
        nearest = (
            f"{to_show(upcoming[0]['scheduled_at'])} · {upcoming[0]['game_title']}"
            if upcoming
            else "—"
        )
        self.summary.config(
            text=f"Подтверждено: {len(confirmed)}    Ждут решения: {len(pending)}    "
            f"Ближайшая игра: {nearest}"
        )

    def on_withdraw(self):
        """Отзывает выбранную заявку после подтверждения."""
        signup_id = selected_id(self.table)
        if signup_id is None:
            raise ValidationError("Заявка", "Выберите заявку в таблице.")
        if messagebox.askyesno("Мои записи", "Отозвать выбранную заявку?"):
            signups.withdraw_signup(self.app.conn, self.app.user, signup_id)
            self.refresh()


class CharactersTab(ttk.Frame):
    """Вкладка «Мои персонажи»: карточки персонажей (макет 09)."""

    def __init__(self, parent, app):
        """Создаёт список персонажей и форму карточки.

        Args:
            parent: Блокнот вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=10)
        self.app = app
        self.character_id = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y")
        ttk.Button(
            left, text="+ Новый", style="Accent.TButton", command=self.clear_form
        ).pack(anchor="w", pady=(0, 8))
        self.table = make_table(
            left, [("Имя", 120), ("Раса", 100), ("Класс", 100), ("Ур.", 40)]
        )
        self.table.master.pack(fill="y", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.Frame(self, padding=(16, 0, 0, 0))
        form.pack(side="left", fill="both", expand=True)
        ttk.Label(form, text="Имя *").pack(anchor="w")
        self.name = ttk.Entry(form, width=40)
        self.name.pack(anchor="w", pady=(0, 6))
        ttk.Label(form, text="Раса").pack(anchor="w")
        self.race = ttk.Combobox(form, values=characters.RACES, width=37)
        self.race.pack(anchor="w", pady=(0, 6))
        ttk.Label(form, text="Класс").pack(anchor="w")
        self.cls = ttk.Combobox(form, values=characters.CLASSES, width=37)
        self.cls.pack(anchor="w", pady=(0, 6))
        ttk.Label(form, text="Уровень * (от 1 до 20)").pack(anchor="w")
        self.level = ttk.Spinbox(form, from_=1, to=20, width=6)
        self.level.pack(anchor="w", pady=(0, 6))
        ttk.Label(form, text="Предыстория").pack(anchor="w")
        self.backstory = make_text(form, height=8)
        self.backstory.pack(fill="both", expand=True)
        buttons = ttk.Frame(form)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Удалить персонажа", command=self.on_delete).pack(
            side="left"
        )
        ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(buttons, text="Отменить", command=self.on_select).pack(
            side="right", padx=6
        )
        self.clear_form()

    def refresh(self):
        """Перечитывает персонажей текущего Игрока."""
        clear_table(self.table)
        for c in characters.list_characters(self.app.conn, self.app.user):
            self.table.insert(
                "",
                "end",
                iid=c["id"],
                values=(c["name"], c["race"] or "—", c["class"] or "—", c["level"]),
            )
        if self.character_id and self.table.exists(self.character_id):
            self.table.selection_set(self.character_id)

    def clear_form(self):
        """Очищает форму для нового персонажа."""
        self.character_id = None
        self.name.delete(0, "end")
        self.race.set("")
        self.cls.set("")
        self.level.set(1)
        set_text(self.backstory, "")
        self.table.selection_remove(self.table.selection())
        self.name.focus()

    def on_select(self, event=None):
        """Загружает выбранного персонажа в форму."""
        character_id = selected_id(self.table)
        if character_id is None:
            return
        c = characters.get_character(self.app.conn, character_id)
        self.character_id = character_id
        self.name.delete(0, "end")
        self.name.insert(0, c["name"])
        self.race.set(c["race"] or "")
        self.cls.set(c["class"] or "")
        self.level.set(c["level"])
        set_text(self.backstory, c["backstory"])

    def on_save(self):
        """Сохраняет карточку персонажа."""
        self.character_id = characters.save_character(
            self.app.conn,
            self.app.user,
            self.name.get(),
            self.race.get(),
            self.cls.get(),
            self.level.get(),
            get_text(self.backstory),
            self.character_id,
        )
        messagebox.showinfo("Мои персонажи", "Карточка персонажа сохранена.")
        self.refresh()

    def on_delete(self):
        """Удаляет персонажа, если у него нет активных заявок (сценарий 13)."""
        if self.character_id is None:
            raise ValidationError("Персонаж", "Выберите персонажа в списке.")
        if messagebox.askyesno("Мои персонажи", "Удалить выбранного персонажа?"):
            characters.delete_character(self.app.conn, self.app.user, self.character_id)
            self.clear_form()
            self.refresh()
