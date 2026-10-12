"""Интеграционные тесты окон: вкладки Мастера и Игрока, профиль, справка, подсказки."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import csv  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest import mock  # noqa: E402

from PySide6.QtCore import QDate  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from gm_hub import settings  # noqa: E402
from gm_hub.logic import auth, characters, games, notes, signups  # noqa: E402
from gm_hub.logic.errors import ValidationError  # noqa: E402
from gm_hub.ui import common, gm_window, profile_window, style  # noqa: E402
from tests import future  # noqa: E402
from tests.test_edge import add_past_game  # noqa: E402
from tests.test_ui import (  # noqa: E402,F401
    UiCase,
    pump,
    setUpModule,
    tearDownModule,
)


class GMTabsTest(UiCase):
    """Вкладки Мастера работают с БД через логику."""

    def test_notes_tab_save_search_delete(self):
        """Заметка сохраняется, находится поиском и удаляется."""
        frame = self.open_as(self.gm, 2)
        tab = frame.tabs[2]
        tab.table.select(self.game_id)
        tab.editor.setPlainText("Сцена 1. Обвал\nВнешность: усталый гном")
        tab.on_save()
        note = notes.get_game_note(self.conn, self.gm, self.game_id)
        self.assertIn("Обвал", note["content"])
        tab.search.setText("обвал")
        self.assertEqual(tab.table.order, [self.game_id])
        tab.search.setText("нет такого текста")
        self.assertEqual(tab.table.order, [])
        tab.search.setText("")
        tab.table.select(self.game_id)
        tab.on_delete()
        self.assertIsNone(notes.get_game_note(self.conn, self.gm, self.game_id))

    def test_dice(self):
        """Кубики показывают результат: число бросков и сумму."""
        tab = self.open_as(self.gm, 2).tabs[2]
        tab.dice_count.setValue(3)
        tab.on_roll(6)
        self.assertTrue(tab.dice_result.text().startswith("3d6:"))
        tab.dice_count.setValue(1)
        tab.on_roll(20)
        self.assertTrue(tab.dice_result.text().startswith("d20:"))

    def test_past_game_summary_and_level_up(self):
        """У прошедшей сессии сохраняются итоги и повышается уровень участникам."""
        past = add_past_game(self.conn, self.gm["id"])
        with self.conn:
            self.conn.execute(
                "INSERT INTO Game_Signups (game_id, character_id, status, "
                "created_at) VALUES (?, ?, 'CONFIRMED', '2026-01-01 10:00')",
                (past, self.hero),
            )
        tab = self.open_as(self.gm, 2).tabs[2]
        tab.table.select(past)
        self.assertTrue(tab.summary_box.isVisible())
        tab.summary.setPlainText("Нашли карту")
        tab.on_save()
        self.assertEqual(games.get_game(self.conn, past)["summary"], "Нашли карту")
        tab.on_level_up()
        self.assertEqual(characters.get_character(self.conn, self.hero)["level"], 5)
        with self.assertRaises(ValidationError):
            tab.on_level_up()  # за ту же сессию повторно нельзя

    def test_export_participants_csv(self):
        """Состав сессии сохраняется в CSV, который открывается в Excel."""
        signup = signups.create_signup(self.conn, self.player, self.game_id, self.hero)
        signups.confirm_signup(self.conn, self.gm, signup)
        tab = self.open_as(self.gm, 2).tabs[2]
        tab.table.select(self.game_id)
        path = str(Path(tempfile.mkdtemp()) / "участники.csv")
        with mock.patch.object(
            gm_window.QFileDialog, "getSaveFileName", return_value=(path, "")
        ):
            tab.on_export()
        with open(path, encoding="utf-8-sig", newline="") as file:
            rows = list(csv.reader(file, delimiter=";"))
        self.assertIn("Пип", [cell for row in rows for cell in row])

    def test_world_tab_crud(self):
        """База мира: ошибка, создание, изменение, фильтр и удаление."""
        tab = self.open_as(self.gm, 3).tabs[3]
        tab.on_save()  # пустая форма
        self.assertTrue(tab.error.isVisible())
        tab.title_entry.setText("Вейла")
        tab.category.setCurrentText("NPC")
        tab.content.setPlainText("Глава гильдии")
        tab.on_save()
        self.assertEqual(len(tab.table.order), 1)
        note_id = tab.table.order[0]
        tab.on_new()
        tab.on_select(note_id)
        self.assertEqual(tab.title_entry.text(), "Вейла")
        tab.title_entry.setText("Вейла Серебряная")
        tab.on_save()
        tab.filter_bar.set_value("LORE")
        tab.refresh()
        self.assertEqual(tab.table.order, [])
        tab.filter_bar.set_value("")
        tab.search.setText("серебр")
        self.assertEqual(len(tab.table.order), 1)
        tab.on_select(note_id)
        tab.on_delete()
        self.assertEqual(notes.list_world_notes(self.conn, self.gm), [])

    def test_stats_and_calendar(self):
        """Статистика и календарь показывают сессии; щелчок открывает сессию."""
        frame = self.open_as(self.gm, 4)
        self.assertEqual(frame.tabs[4].values["planned"].text(), "1")
        calendar = self.open_as(self.gm, 5).tabs[5]
        calendar.turn(1)
        calendar.turn(-1)
        calendar.go_today()
        calendar.open_game(games.get_game(self.conn, self.game_id))
        self.assertEqual(self.app.screen.shown, 0)
        self.assertEqual(self.app.screen.tabs[0].title_entry.text(), "Шахта Эхо")

    def test_signups_tab_reject_with_reason(self):
        """Мастер отклоняет заявку с причиной, Игрок её видит."""
        signup = signups.create_signup(self.conn, self.player, self.game_id, self.hero)
        tab = self.open_as(self.gm, 1).tabs[1]
        tab.table.select(signup)
        self.assertEqual(tab.char_name.text(), "Пип")
        with mock.patch.object(gm_window, "ask_text", lambda *a, **k: "Мест нет"):
            tab.on_reject(signup)
        row = signups.list_for_player(self.conn, self.player)[0]
        self.assertEqual((row["status"], row["reason"]), ("REJECTED", "Мест нет"))
        tab.status_box.setCurrentText("Отклонена")
        tab.load_signups()
        self.assertEqual(len(tab.table.order), 1)

    def test_other_master_sees_nothing(self):
        """Другой Мастер не видит чужих сессий, заявок и заметок."""
        auth.register(self.conn, "Мастер Два", "gm2", "1234", "1234", "GM")
        other = auth.login_user(self.conn, "gm2", "1234")
        frame = self.open_as(other, 0)
        self.assertEqual(frame.tabs[0].table.order, [])
        self.assertEqual(self.open_as(other, 2).tabs[2].table.order, [])


class PlayerTabsTest(UiCase):
    """Вкладки Игрока."""

    def test_my_signups_withdraw_and_periods(self):
        """«Мои записи»: список, отзыв заявки, прошедшие, двойной щелчок."""
        signup = signups.create_signup(self.conn, self.player, self.game_id, self.hero)
        frame = self.open_as(self.player, 1)
        tab = frame.tabs[1]
        self.assertEqual(tab.table.order, [signup])
        tab.table.selected = None
        with self.assertRaises(ValidationError):
            tab.on_withdraw()
        tab.on_double(signup)
        self.assertEqual(frame.shown, 0)  # открылась витрина
        tab = self.open_as(self.player, 1).tabs[1]
        tab.period.set_value("past")
        tab.refresh()
        self.assertEqual(tab.table.order, [])
        tab.period.set_value("future")
        tab.refresh()
        tab.table.select(signup)
        tab.on_withdraw()
        self.assertEqual(signups.list_for_player(self.conn, self.player), [])

    def test_characters_tab_cycle(self):
        """«Мои персонажи»: создание, изменение, отмена правок, удаление."""
        tab = self.open_as(self.player, 2).tabs[2]
        tab.on_new()
        tab.name.setText("Тория")
        tab.race.setCurrentText("Дварф")
        tab.cls.setCurrentText("Воин")
        tab.backstory.setPlainText("Кузнец")
        tab.on_save()
        self.assertTrue(tab.error.isVisible())  # «Карточка сохранена»
        new_id = tab.character_id
        self.assertEqual(characters.get_character(self.conn, new_id)["class"], "Воин")
        tab.name.setText("Тория II")
        tab.reload()  # «Отменить»
        self.assertEqual(tab.name.text(), "Тория")
        tab.on_delete()
        self.assertIsNone(characters.get_character(self.conn, new_id))

    def test_showcase_filters_and_search(self):
        """Витрина: фильтры по дате и местам, поиск Мастера, двойной щелчок."""
        frame = self.open_as(self.player, 0)
        tab = frame.tabs[0]
        self.assertEqual(tab.table.order, [self.game_id])
        tab.only_free.setChecked(True)
        self.assertEqual(tab.table.order, [self.game_id])
        tab.period.set_value("7 дней")
        tab.load_games()
        self.assertEqual(tab.table.order, [self.game_id])
        tab.search.setText("нет такого")
        self.assertEqual(tab.table.order, [])
        tab.search.setText("")
        tab.period.set_value("Все даты")
        tab.load_games()
        tab.on_double(self.game_id)
        self.assertEqual(tab.table.selected, self.game_id)
        self.assertIn("свободно", tab.info_when.text())

    def test_reminder_for_confirmed_game(self):
        """Над витриной — напоминание о подтверждённой игре в ближайшие дни."""
        date, time = future(2)  # напоминание — только о играх в ближайшие 3 дня
        soon = games.save_game(self.conn, self.gm, "Скоро", "", date, time, 2)
        signup = signups.create_signup(self.conn, self.player, soon, self.hero)
        signups.confirm_signup(self.conn, self.gm, signup)
        tab = self.open_as(self.player, 0).tabs[0]
        self.assertTrue(tab.reminder.isVisible())
        self.assertIn("Скоро", tab.reminder.text.text())


class DialogsTest(UiCase):
    """Профиль, справка, подсказки логинов, календарь выбора даты."""

    def setUp(self):
        """Профиль и справка могут спрашивать подтверждение."""
        super().setUp()
        patch = mock.patch.object(profile_window, "ask", lambda *a, **k: True)
        patch.start()
        self.addCleanup(patch.stop)

    def test_profile_save(self):
        """В профиле меняются ФИО и пароль; неверный пароль — ошибка."""
        self.open_as(self.player, 0)
        window = profile_window.ProfileWindow(self.app)
        window.entries["ФИО *"].setText("Новое Имя")
        window.entries["Текущий пароль *"].setText("0000")
        with self.assertRaises(ValidationError):
            window.on_save()
        window.entries["Текущий пароль *"].setText("1234")
        window.entries["Новый пароль"].setText("5678")
        window.entries["Повтор нового"].setText("5678")
        window.on_save()
        user = auth.login_user(self.conn, "gleb", "5678")
        self.assertEqual(user["full_name"], "Новое Имя")
        self.assertEqual(self.app.user["full_name"], "Новое Имя")

    def test_profile_delete_account(self):
        """Аккаунт без данных удаляется, открывается окно входа."""
        auth.register(self.conn, "Пустой", "empty", "1234", "1234", "PLAYER")
        user = auth.login_user(self.conn, "empty", "1234")
        self.open_as(user, 0)
        window = profile_window.ProfileWindow(self.app)
        window.entries["Текущий пароль *"].setText("1234")
        window.on_delete()
        self.assertEqual(type(self.app.screen).__name__, "LoginFrame")
        with self.assertRaises(ValidationError):
            auth.login_user(self.conn, "empty", "1234")

    def test_profile_large_text_toggle(self):
        """Переключатель «Крупный текст» сохраняет настройку."""
        self.open_as(self.gm, 0)
        window = profile_window.ProfileWindow(self.app)
        try:
            window.large_text.setChecked(True)
            self.assertTrue(settings.get_setting("large_text"))
        finally:
            settings.write_setting("large_text", False)
            style.apply(QApplication.instance())

    def test_help_window(self):
        """F1 и ссылка «Справка» открывают окно справки, повтор заменяет его."""
        self.open_as(self.gm, 0)
        self.app.show_help()
        first = self.app.help
        self.assertTrue(first.isVisible())
        self.app.show_help()
        self.assertIsNot(self.app.help, first)
        self.assertIn(
            "Расписание", [w.text() for w in self.app.help.findChildren(QLabel)]
        )
        self.app.help.close()

    def test_login_hints(self):
        """Подсказки логинов: показ, выбор стрелками, выбор щелчком, забыть."""
        settings.remember_login("gm")
        settings.remember_login("gleb")
        self.app.show_login()
        screen = self.app.screen
        hints = screen.hints
        screen.login.setText("")
        hints.show()
        self.assertEqual(hints.items, ["gleb", "gm"])
        hints.move(1)
        self.assertEqual(hints.picked(), "gleb")
        screen.on_login_enter()  # Enter с выбранной подсказкой
        self.assertEqual(screen.login.text(), "gleb")
        hints.forget("gm")
        self.assertNotIn("gm", settings.recent_logins())
        screen.login.setText("zzz")
        hints.show()
        self.assertFalse(hints.box.isVisible())

    def test_date_picker(self):
        """Календарь подставляет выбранную дату в поле."""
        tab = self.open_as(self.gm, 0).tabs[0]
        picker = common.DatePicker(tab.date_entry)
        day = QDate.currentDate().addDays(5)
        picker.pick(day)
        self.assertEqual(tab.date_entry.text(), day.toString("dd.MM.yyyy"))

    def test_banner_and_pill(self):
        """Плашка показывает и скрывает сообщения, таблетка создаётся."""
        banner = common.Banner()
        banner.show_message("Ошибка", "error")
        self.assertEqual(banner.text.text(), "Ошибка")
        banner.show_message("Готово", "ok", auto_hide=False)
        self.assertFalse(banner.timer.isActive())
        banner.hide()
        for kind in ("ok", "warn", "bad", "grey", "chip"):
            self.assertEqual(common.Pill("текст", kind).text(), "текст")


if __name__ == "__main__":
    unittest.main()
