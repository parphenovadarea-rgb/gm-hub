"""Окно Игрока: вкладки «Витрина сессий», «Мои записи», «Мои персонажи».

Макеты 07–09. Вкладок «Сюжетный блокнот» и «База мира» здесь нет
(сценарий 12 п. 6.1 ТЗ).
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.config import now_str, to_short, to_show
from gm_hub.logic import characters, games, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    Banner,
    ChoiceCards,
    MainFrame,
    card,
    clear_table,
    field,
    get_text,
    is_soon,
    make_table,
    make_text,
    segmented,
    selected_id,
    set_text,
)


def character_info(c) -> str:
    """Возвращает подпись персонажа: «Полурослик · Плут · 4 ур.»."""
    return f"{c['race'] or '—'} · {c['class'] or '—'} · {c['level']} ур."


class PlayerFrame(MainFrame):
    """Главное окно Игрока с вкладками."""

    def __init__(self, app):
        """Создаёт шапку и вкладки.

        Args:
            app: Приложение (app.conn, app.user).
        """
        super().__init__(
            app,
            [
                ("Витрина сессий", ShowcaseTab),
                ("Мои записи", MySignupsTab),
                ("Мои персонажи", CharactersTab),
            ],
        )


class ShowcaseTab(ttk.Frame):
    """Вкладка «Витрина сессий» и запись на игру (макет 07)."""

    def __init__(self, parent, app):
        """Создаёт таблицу сессий и форму заявки.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=16)
        self.app = app

        form = card(self, "Запись на сессию")
        form.master.pack(side="right", fill="y", padx=(16, 0))
        self.info_title = ttk.Label(
            form, text="Выберите сессию в таблице", style="Bold.TLabel", width=36
        )
        self.info_title.pack(anchor="w")
        self.info_when = ttk.Label(form, style="Muted.TLabel")
        self.info_when.pack(anchor="w")
        field(form, "Персонаж *")
        self.characters = ChoiceCards(form)
        self.characters.pack(fill="x")
        field(form, "Комментарий Мастеру (необязательно)")
        self.comment = ttk.Entry(form)
        self.comment.pack(fill="x", ipady=2)
        self.send_button = ttk.Button(
            form, text="Отправить заявку", style="Accent.TButton", command=self.on_send
        )
        self.send_button.pack(fill="x", pady=(14, 0), ipady=3)
        self.error = Banner(form, fill="x", pady=(10, 0), before=self.send_button)

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.only_free = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top,
            text="Только со свободными местами",
            variable=self.only_free,
            command=self.refresh,
        ).pack(side="left")
        ttk.Label(top, text="Сортировка по дате", style="Muted.TLabel").pack(
            side="right"
        )

        self.table = make_table(
            self,
            [
                ("Сессия", 330),
                ("Когда", 150),
                ("Свободно", 100),
                ("Мастер", 170),
                ("Моя заявка", 150),
            ],
            tall=True,
        )
        self.table.master.pack(fill="both", expand=True, pady=(12, 0))
        self.table.bind("<<TreeviewSelect>>", self.on_select)

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
            soon = is_soon(game["scheduled_at"])
            self.table.insert(
                "",
                "end",
                iid=game["id"],
                tags=("soon",) if soon else (),
                values=(
                    f"{game['title']}\n{game['description'] or ''}",
                    to_show(game["scheduled_at"]) + ("\nскоро" if soon else ""),
                    f"{free} из {game['max_players']}",
                    game["gm_name"],
                    ", ".join(my_status.get(game["id"], [])) or "—",
                ),
            )

        self.characters.set_options(
            [
                (c["id"], c["name"], character_info(c))
                for c in characters.list_characters(conn, user)
            ]
        )
        self.error.hide()

    def on_select(self, event=None):
        """Показывает выбранную сессию в форме заявки."""
        game_id = selected_id(self.table)
        if game_id is None:
            return
        game = games.get_game(self.app.conn, game_id)
        free = games.free_seats(game["max_players"], game["confirmed"])
        self.info_title.config(text=game["title"])
        self.info_when.config(
            text=f"{to_show(game['scheduled_at'])} · "
            f"свободно {free} из {game['max_players']}"
        )
        self.error.hide()

    def on_send(self):
        """Подаёт заявку выбранным персонажем (сценарии 5–7)."""
        game_id = selected_id(self.table)
        try:
            signups.create_signup(
                self.app.conn,
                self.app.user,
                game_id,
                self.characters.get(),
                self.comment.get(),
            )
        except ValidationError as error:
            self.error.show(error.message)
            return
        title = games.get_game(self.app.conn, game_id)["title"]
        self.comment.delete(0, "end")
        # Как в прототипе: после отправки открываются «Мои записи» с сообщением.
        main = self.app.screen
        main.show_tab(1)
        main.tabs[1].banner.show(
            f"Заявка на «{title}» отправлена. Статус: на рассмотрении.", "ok"
        )


class MySignupsTab(ttk.Frame):
    """Вкладка «Мои записи»: статусы своих заявок (макет 08)."""

    PERIODS = [("Предстоящие", "future"), ("Прошедшие", "past")]

    def __init__(self, parent, app):
        """Создаёт таблицу заявок.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=16)
        self.app = app
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.banner = Banner(self, fill="x", pady=(0, 12), before=top)
        self.period = tk.StringVar(value="future")
        segmented(top, self.PERIODS, self.period, self.refresh).pack(side="left")
        ttk.Button(
            top,
            text="Отозвать заявку",
            style="Danger.TButton",
            command=self.on_withdraw,
        ).pack(side="right")
        self.table = make_table(
            self,
            [
                ("Сессия", 240),
                ("Когда", 140),
                ("Персонаж", 120),
                ("Мой комментарий", 200),
                ("Статус", 140),
                ("Решение", 120),
            ],
        )
        self.table.master.pack(fill="both", expand=True, pady=12)
        self.summary = ttk.Label(self, style="Muted.TLabel")
        self.summary.pack(anchor="w")

    def refresh(self):
        """Перечитывает заявки текущего Игрока (сценарий 14)."""
        self.banner.hide()
        clear_table(self.table)
        rows = signups.list_for_player(self.app.conn, self.app.user)
        now = now_str()
        for row in rows:
            upcoming = row["scheduled_at"] >= now
            if upcoming != (self.period.get() == "future"):
                continue
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
                    to_short(row["decided_at"]),
                ),
            )
        confirmed = [r for r in rows if r["status"] == "CONFIRMED"]
        pending = [r for r in rows if r["status"] == "PENDING"]
        upcoming = [r for r in confirmed if r["scheduled_at"] >= now]
        nearest = (
            f"{to_show(upcoming[0]['scheduled_at'])} · {upcoming[0]['game_title']}"
            if upcoming
            else "—"
        )
        self.summary.config(
            text=f"Подтверждено: {len(confirmed)}     Ждут решения: {len(pending)}     "
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
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, padding=16)
        self.app = app
        self.character_id = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="y")
        head = ttk.Frame(left)
        head.pack(fill="x", pady=(0, 8))
        ttk.Label(head, text="Персонажи", style="Bold.TLabel").pack(side="left")
        ttk.Button(head, text="+ Новый", command=self.clear_form).pack(side="right")
        self.table = make_table(left, [("Персонаж", 260)], tall=True)
        self.table.master.pack(fill="y", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = card(self)
        form.master.pack(side="left", fill="both", expand=True, padx=(16, 0))
        row = ttk.Frame(form)
        row.pack(fill="x")
        boxes = [ttk.Frame(row) for _ in range(3)]
        for index, box in enumerate(boxes):
            box.grid(row=0, column=index, sticky="ew", padx=(0, 12) if index < 2 else 0)
        row.columnconfigure((0, 1, 2), weight=1, uniform="col")
        field(boxes[0], "Имя *")
        self.name = ttk.Entry(boxes[0])
        self.name.pack(fill="x", ipady=2)
        field(boxes[1], "Раса")
        self.race = ttk.Combobox(boxes[1], values=characters.RACES)
        self.race.pack(fill="x", ipady=2)
        field(boxes[2], "Класс")
        self.cls = ttk.Combobox(boxes[2], values=characters.CLASSES)
        self.cls.pack(fill="x", ipady=2)
        field(form, "Уровень *")
        self.level = ttk.Spinbox(form, from_=1, to=20, width=8)
        self.level.pack(anchor="w")
        ttk.Label(form, text="от 1 до 20", style="Small.TLabel").pack(anchor="w")
        field(form, "Предыстория")
        self.backstory = make_text(form, height=7)
        self.backstory.pack(fill="both", expand=True)
        buttons = ttk.Frame(form)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(
            buttons,
            text="Удалить персонажа",
            style="Danger.TButton",
            command=self.on_delete,
        ).pack(side="left")
        ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(buttons, text="Отменить", command=self.on_select).pack(
            side="right", padx=6
        )
        self.error = Banner(form, fill="x", pady=(10, 0), before=buttons)
        self.clear_form()

    def refresh(self):
        """Перечитывает персонажей текущего Игрока."""
        clear_table(self.table)
        for c in characters.list_characters(self.app.conn, self.app.user):
            self.table.insert(
                "", "end", iid=c["id"], values=(f"{c['name']}\n{character_info(c)}",)
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
        self.error.hide()
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
        self.error.hide()

    def on_save(self):
        """Сохраняет карточку персонажа; ошибку показывает в форме."""
        try:
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
        except ValidationError as error:
            self.error.show(error.message)
            return
        self.error.show("Карточка персонажа сохранена.", "ok")
        self.refresh()

    def on_delete(self):
        """Удаляет персонажа, если у него нет активных заявок (сценарий 13)."""
        if self.character_id is None:
            self.error.show("Выберите персонажа в списке.")
            return
        if not messagebox.askyesno("Мои персонажи", "Удалить выбранного персонажа?"):
            return
        try:
            characters.delete_character(self.app.conn, self.app.user, self.character_id)
        except ValidationError as error:
            self.error.show(error.message)
            return
        self.clear_form()
        self.refresh()
