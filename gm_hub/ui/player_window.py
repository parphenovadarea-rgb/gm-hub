"""Окно Игрока: вкладки «Витрина сессий», «Мои записи», «Мои персонажи».

Макеты 07–09. Игрок выбирает Мастера (можно найти по имени) и видит
витрину его сессий. Вкладок «Сюжетный блокнот» и «База мира» здесь нет
(сценарий 12 п. 6.1 ТЗ).
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gm_hub.config import now_str, to_short, to_show
from gm_hub.logic import auth, characters, games, signups
from gm_hub.logic.errors import ValidationError
from gm_hub.ui.common import (
    px,
    Banner,
    ChoiceCards,
    MainFrame,
    card,
    field,
    get_text,
    is_soon,
    make_text,
    segmented,
    set_text,
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


class ShowcaseTab(Tab):
    """Вкладка «Витрина сессий»: выбор Мастера и запись на игру (макет 07)."""

    def __init__(self, parent, app):
        """Создаёт список Мастеров, таблицу сессий и форму заявки.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        self.master_id = None

        # Слева — выбор Мастера с поиском по имени.
        left = ttk.Frame(self, style="Page.TFrame")
        left.pack(side="left", fill="y", padx=px((0, 12)))
        ttk.Label(left, text="Мастер", style="PageBold.TLabel").pack(anchor="w")
        ttk.Label(left, text="⌕ найти по имени", style="Page.TLabel").pack(anchor="w")
        self.search = ttk.Entry(left, width=16)
        self.search.pack(fill="x", pady=px((4, 10)))
        self.search.bind("<KeyRelease>", lambda e: self.load_masters())
        self.masters = RowTable(
            left, [("Мастера", 150, True)], header=False, on_select=self.on_master
        )
        self.masters.pack(fill="y", expand=True)

        form = card(self, "Запись на сессию")
        form.master.pack(side="right", fill="y", padx=px((16, 0)))
        self.info_title = ttk.Label(
            form,
            text="Выберите сессию в таблице",
            style="Bold.TLabel",
            width=28,
            wraplength=px(230),
        )
        self.info_title.pack(anchor="w")
        self.info_when = ttk.Label(form, style="Muted.TLabel")
        self.info_when.pack(anchor="w")
        field(form, "Персонаж *")
        self.characters = ChoiceCards(form)
        self.characters.pack(fill="x")
        field(form, "Комментарий Мастеру (необязательно)")
        self.comment = ttk.Entry(form)
        self.comment.pack(fill="x")
        self.send_button = ttk.Button(
            form, text="Отправить заявку", style="Accent.TButton", command=self.on_send
        )
        self.send_button.pack(fill="x", pady=px((14, 0)))
        self.error = Banner(form, fill="x", pady=px((10, 0)), before=self.send_button)
        ttk.Label(
            form,
            text="Без выбранного персонажа кнопка покажет:\n"
            "«Выберите персонажа для заявки».",
            style="Small.TLabel",
        ).pack(anchor="w", pady=px((10, 0)))

        top = ttk.Frame(self, style="Page.TFrame")
        top.pack(fill="x")
        self.master_label = ttk.Label(
            top, style="PageInk.TLabel", font=("Georgia", 13, "bold")
        )
        self.master_label.pack(side="left")
        self.only_free = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top,
            text="Только со свободными местами",
            variable=self.only_free,
            command=self.load_games,
            style="Page.TCheckbutton",
        ).pack(side="right")

        self.table = RowTable(
            self,
            [
                ("Сессия", 210, True),
                ("Когда", 140, False),
                ("Свободно", 75, False),
                ("Моя заявка", 125, False),
            ],
            on_select=self.on_select,
        )
        self.table.pack(fill="both", expand=True, pady=px((12, 0)))

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

    def load_masters(self):
        """Показывает Мастеров, подходящих под поиск по имени."""
        found = auth.list_masters(self.app.conn, self.search.get())
        self.masters.clear("Мастер не найден")
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
        if self.master_id not in ids:
            self.master_id = ids[0] if ids else None
        if self.master_id is not None:
            self.masters.select(self.master_id, notify=False)
        self.load_games()

    def on_master(self, master_id):
        """Выбирает Мастера и показывает его сессии."""
        self.master_id = master_id
        self.load_games()

    def load_games(self):
        """Показывает предстоящие сессии выбранного Мастера."""
        conn, user = self.app.conn, self.app.user
        self.info_title.config(text="Выберите сессию в таблице")
        self.info_when.config(text="")
        if self.master_id is None:
            self.master_label.config(text="Мастер не выбран")
            self.table.clear("Выберите Мастера слева")
            return
        master = next(m for m in auth.list_masters(conn) if m["id"] == self.master_id)
        self.master_label.config(text=f"Сессии Мастера: {master['full_name']}")

        my_status = {}  # id сессии -> статусы моих заявок
        for row in signups.list_for_player(conn, user):
            my_status.setdefault(row["game_id"], []).append(row["status"])

        self.table.clear("У этого Мастера нет предстоящих сессий")
        shown = 0
        for game in games.list_games(conn, gm_id=self.master_id):
            free = games.free_seats(game["max_players"], game["confirmed"])
            if self.only_free.get() and free <= 0:
                continue
            title = [("bold", game["title"])]
            if game["description"]:
                title.append(("muted", game["description"]))
            when = [to_short(game["scheduled_at"])]
            if is_soon(game["scheduled_at"]):
                when.append(("small", "СКОРО"))
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
        self.info_title.config(text=game["title"])
        self.info_when.config(
            text=f"{to_show(game['scheduled_at'])} · "
            f"свободно {free} из {game['max_players']}"
        )
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


class MySignupsTab(Tab):
    """Вкладка «Мои записи»: статусы своих заявок у всех Мастеров (макет 08)."""

    PERIODS = [("Предстоящие", "future"), ("Прошедшие", "past")]

    def __init__(self, parent, app):
        """Создаёт таблицу заявок.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        top = ttk.Frame(self, style="Page.TFrame")
        top.pack(fill="x")
        self.banner = Banner(self, fill="x", pady=px((0, 12)), before=top)
        self.period = tk.StringVar(value="future")
        segmented(top, self.PERIODS, self.period, self.refresh).pack(side="left")
        ttk.Button(
            top,
            text="Отозвать заявку",
            style="Danger.TButton",
            command=self.on_withdraw,
        ).pack(side="right")
        self.table = RowTable(
            self,
            [
                ("Сессия", 260, True),
                ("Когда", 140, False),
                ("Персонаж", 110, False),
                ("Мой комментарий", 180, True),
                ("Статус", 150, False),
                ("Решение", 100, False),
            ],
        )
        self.table.pack(fill="both", expand=True, pady=px((12, 0)))

    def refresh(self):
        """Перечитывает заявки текущего Игрока (сценарий 14)."""
        self.banner.hide()
        self.table.clear("Заявок нет")
        rows = signups.list_for_player(self.app.conn, self.app.user)
        now = now_str()
        for row in rows:
            upcoming = row["scheduled_at"] >= now
            if upcoming != (self.period.get() == "future"):
                continue
            self.table.add(
                row["id"],
                [
                    (
                        "stack",
                        [
                            ("bold", row["game_title"]),
                            ("muted", f"Мастер: {row['gm_name']}"),
                        ],
                    ),
                    to_show(row["scheduled_at"]),
                    row["character_name"],
                    ("muted", row["comment"] or "—"),
                    status_cell(row),
                    ("muted", to_short(row["decided_at"])),
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

    def on_withdraw(self):
        """Отзывает выбранную заявку после подтверждения."""
        signup_id = self.table.selected
        if signup_id is None:
            raise ValidationError("Заявка", "Выберите заявку в таблице.")
        if messagebox.askyesno("Мои записи", "Отозвать выбранную заявку?"):
            signups.withdraw_signup(self.app.conn, self.app.user, signup_id)
            self.refresh()


class CharactersTab(Tab):
    """Вкладка «Мои персонажи»: карточки персонажей (макет 09)."""

    def __init__(self, parent, app):
        """Создаёт список персонажей и форму карточки.

        Args:
            parent: Область вкладок.
            app: Приложение.
        """
        super().__init__(parent, app)
        self.character_id = None

        left = card(self, "Персонажи", action=("+ Новый", self.clear_form))
        left.master.pack(side="left", fill="y")
        left.configure(padding=0)
        self.table = RowTable(
            left,
            [("Персонаж", 240, True)],
            header=False,
            on_select=self.on_select,
            border=False,
        )
        self.table.pack(fill="both", expand=True)

        form = card(self)
        form.master.pack(side="left", fill="both", expand=True, padx=px((16, 0)))
        row = ttk.Frame(form)
        row.pack(fill="x")
        boxes = [ttk.Frame(row) for _ in range(3)]
        for index, box in enumerate(boxes):
            box.grid(
                row=0, column=index, sticky="ew", padx=px((0, 12)) if index < 2 else 0
            )
        row.columnconfigure((0, 1, 2), weight=1, uniform="col")
        field(boxes[0], "Имя *")
        self.name = ttk.Entry(boxes[0])
        self.name.pack(fill="x")
        field(boxes[1], "Раса")
        self.race = ttk.Combobox(boxes[1], values=characters.RACES)
        self.race.pack(fill="x")
        field(boxes[2], "Класс")
        self.cls = ttk.Combobox(boxes[2], values=characters.CLASSES)
        self.cls.pack(fill="x")
        field(form, "Предыстория")
        self.backstory = make_text(form, height=7)
        self.backstory.pack(fill="both", expand=True)
        buttons = ttk.Frame(form)
        buttons.pack(fill="x", pady=px((10, 0)))
        ttk.Button(
            buttons,
            text="Удалить персонажа",
            style="Danger.TButton",
            command=self.on_delete,
        ).pack(side="left")
        ttk.Button(
            buttons, text="Сохранить", style="Accent.TButton", command=self.on_save
        ).pack(side="right")
        ttk.Button(buttons, text="Отменить", command=self.reload).pack(
            side="right", padx=px(6)
        )
        self.error = Banner(form, fill="x", pady=px((10, 0)), before=buttons)
        self.clear_form()

    def refresh(self):
        """Перечитывает персонажей текущего Игрока с числом их заявок."""
        counts = {}  # id персонажа -> {статус: количество}
        for row in signups.list_for_player(self.app.conn, self.app.user):
            by_status = counts.setdefault(row["character_id"], {})
            by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        self.table.clear("Персонажей пока нет")
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
        self.name.delete(0, "end")
        self.race.set("")
        self.cls.set("")
        # Уровень в карточке не выбирается: у нового персонажа он 1 (в БД поле
        # обязательное), у существующего сохраняется прежний.
        self.level = 1
        set_text(self.backstory, "")
        self.error.hide()
        self.refresh()
        self.name.focus()

    def on_select(self, character_id):
        """Запоминает выбранного персонажа и загружает его в форму."""
        self.character_id = character_id
        self.reload()

    def reload(self):
        """Загружает выбранного персонажа в форму (отменяет правки)."""
        if self.character_id is None:
            return
        c = characters.get_character(self.app.conn, self.character_id)
        self.name.delete(0, "end")
        self.name.insert(0, c["name"])
        self.race.set(c["race"] or "")
        self.cls.set(c["class"] or "")
        self.level = c["level"]
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
                self.level,
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
