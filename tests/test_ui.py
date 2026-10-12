"""Тесты окон: вход, формы, клавиши, права, темы (без экрана, режим offscreen)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile  # noqa: E402
import unittest  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest import mock  # noqa: E402

from PySide6.QtCore import QLocale, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from gm_hub import settings  # noqa: E402
from gm_hub.logic import auth, characters, games, signups  # noqa: E402
from gm_hub.ui import common, gm_window, player_window, style, theme  # noqa: E402
from gm_hub.ui.app import App  # noqa: E402
from tests import future, make_db  # noqa: E402

qt = None
settings_patch = None


def setUpModule():
    """Создаёт приложение Qt и подменяет файл настроек на временный."""
    global qt, settings_patch
    folder = tempfile.mkdtemp()
    settings_patch = mock.patch.object(
        settings, "SETTINGS_PATH", Path(folder) / "settings.json"
    )
    settings_patch.start()
    qt = QApplication.instance() or QApplication([])
    QLocale.setDefault(QLocale(QLocale.Russian, QLocale.Russia))
    theme.set_theme("light")
    style.apply(qt)


def tearDownModule():
    """Возвращает настоящий путь настроек и светлую тему."""
    settings_patch.stop()
    theme.set_theme("light")


def pump():
    """Даёт Qt обработать накопившиеся события."""
    for _ in range(6):
        qt.processEvents()


class UiCase(unittest.TestCase):
    """Основа тестов окон: БД в памяти, Мастер, Игрок, сессия и персонаж."""

    def setUp(self):
        """Создаёт данные и главное окно (окна сообщений отвечают сами)."""
        self.conn = make_db()
        auth.register(self.conn, "Мастер Агыг", "agyg", "1234", "1234", "GM")
        auth.register(self.conn, "Игрок Глеб", "gleb", "1234", "1234", "PLAYER")
        self.gm = auth.login_user(self.conn, "agyg", "1234")
        self.player = auth.login_user(self.conn, "gleb", "1234")
        date, time = future(5)
        self.game_id = games.save_game(
            self.conn, self.gm, "Шахта Эхо", "Спуск", date, time, 1
        )
        self.hero = characters.save_character(
            self.conn, self.player, "Пип", "Полурослик", "Плут", 4, "Плут"
        )
        self.asked = []  # тексты окон сообщений
        patches = [
            mock.patch.object(
                QMessageBox, "exec", lambda box: (self.asked.append(box.text()), 0)[1]
            ),
            mock.patch.object(gm_window, "ask", lambda *a, **k: True),
            mock.patch.object(player_window, "ask", lambda *a, **k: True),
            mock.patch.object(common, "ask_save", lambda parent: None),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.app = App(self.conn)
        self.app.resize(1360, 800)
        self.app.show()
        self.addCleanup(self.close_app)

    def close_app(self):
        """Закрывает окно после теста."""
        self.app.screen.hide() if self.app.screen else None
        self.app.close()
        self.app.deleteLater()
        pump()
        theme.set_theme("light")
        style.apply(qt)

    def open_as(self, user, tab=0):
        """Открывает кабинет пользователя на нужной вкладке и возвращает его."""
        self.app.open_main(user)
        pump()
        frame = self.app.screen
        frame.show_tab(tab)
        pump()
        return frame


class LoginTest(UiCase):
    """Окна входа и регистрации."""

    def test_first_screen_is_login(self):
        """Если пользователи есть, открывается окно входа."""
        self.assertEqual(type(self.app.screen).__name__, "LoginFrame")

    def test_wrong_password_shows_banner(self):
        """Неверный пароль — красная плашка, кабинет не открывается."""
        screen = self.app.screen
        screen.login.setText("agyg")
        screen.password.setText("0000")
        screen.on_login()
        self.assertTrue(screen.error.isVisible())
        self.assertIn("Неверный логин", screen.error.text.text())
        self.assertEqual(type(self.app.screen).__name__, "LoginFrame")

    def test_login_opens_cabinet_by_role(self):
        """Мастер попадает в кабинет Мастера, Игрок — в кабинет Игрока."""
        for login, name in (("agyg", "GMFrame"), ("gleb", "PlayerFrame")):
            self.app.show_login()
            screen = self.app.screen
            screen.login.setText(login)
            screen.password.setText("1234")
            screen.on_login()
            self.assertEqual(type(self.app.screen).__name__, name)

    def test_login_is_remembered(self):
        """После входа логин попадает в подсказки на этом компьютере."""
        screen = self.app.screen
        screen.login.setText("agyg")
        screen.password.setText("1234")
        screen.on_login()
        self.assertIn("agyg", settings.recent_logins())

    def test_register_error_in_banner(self):
        """Регистрация без логина показывает ошибку и не создаёт аккаунт."""
        self.app.show_register()
        screen = self.app.screen
        screen.entries["ФИО"].setText("Новый Игрок")
        screen.role.select("PLAYER")
        screen.on_register()
        self.assertTrue(screen.error.isVisible())


class ScheduleTest(UiCase):
    """Вкладка «Расписание» Мастера."""

    def setUp(self):
        """Открывает кабинет Мастера."""
        super().setUp()
        self.frame = self.open_as(self.gm, 0)
        self.tab = self.frame.tabs[0]

    def fill(self, title, date, time):
        """Заполняет форму новой сессии."""
        self.tab.clear_form()
        self.tab.title_entry.setText(title)
        self.tab.date_entry.setText(date)
        self.tab.time_entry.setText(time)

    def titles(self):
        """Названия сессий в таблице (строчными)."""
        return [self.tab.table.rows[i]["values"][0] for i in self.tab.table.order]

    def test_save_creates_session(self):
        """Кнопка «Опубликовать» создаёт сессию."""
        date, time = future(9)
        self.fill("Новая игра", date, time)
        self.tab.on_save()
        self.assertIn("новая игра", self.titles())

    def test_past_date_is_rejected(self):
        """Дата в прошлом не принимается — ошибка в плашке формы."""
        self.fill("Старая игра", "01.01.2020", "18:00")
        self.tab.on_save()
        self.assertTrue(self.tab.error.isVisible())
        self.assertNotIn("старая игра", self.titles())

    def test_ctrl_s_saves(self):
        """Ctrl+S сохраняет форму на открытой вкладке."""
        date, time = future(10)
        self.fill("Игра по Ctrl+S", date, time)
        self.tab.title_entry.setFocus()
        QTest.keyClick(self.tab.title_entry, Qt.Key_S, Qt.ControlModifier)
        pump()
        self.assertIn("игра по ctrl+s", self.titles())

    def test_delete_key_in_field_does_not_delete(self):
        """Delete в поле ввода удаляет символ, а не выбранную строку."""
        self.tab.table.select(self.game_id)
        self.tab.title_entry.setFocus()
        self.tab.title_entry.setCursorPosition(0)
        QTest.keyClick(self.tab.title_entry, Qt.Key_Delete)
        pump()
        self.assertEqual(len(self.tab.table.order), 1)
        self.assertFalse(self.asked)

    def test_delete_button_only_on_cancelled(self):
        """Кнопка «Удалить» видна только на фильтре «Отменённые»."""
        self.assertFalse(self.tab.delete_button.isVisible())
        self.tab.period.set_value("CANCELLED")
        self.tab.refresh()
        pump()
        self.assertTrue(self.tab.delete_button.isVisible())

    def test_cancel_then_delete(self):
        """Сессию можно отменить, затем удалить из отменённых."""
        self.tab.table.select(self.game_id)
        self.tab.on_cancel()
        self.assertEqual(games.get_game(self.conn, self.game_id)["status"], "CANCELLED")
        self.tab.period.set_value("CANCELLED")
        self.tab.refresh()
        self.tab.table.select(self.game_id)
        self.tab.on_delete()
        self.assertIsNone(games.get_game(self.conn, self.game_id))

    def test_unsaved_form_blocks_leaving(self):
        """С несохранённой формой нельзя уйти с вкладки, пока не ответили."""
        self.tab.clear_form()
        self.tab.title_entry.setText("Не сохранено")
        self.assertFalse(self.app.can_leave())  # ask_save отвечает «Отмена»
        self.frame.show_tab(1)
        self.assertEqual(self.frame.shown, 0)

    def test_escape_clears_form(self):
        """Esc в форме запускает очистку (с вопросом, если есть правки)."""
        self.tab.title_entry.setText("что-то")
        self.tab.title_entry.setFocus()
        with mock.patch.object(common, "ask_save", lambda parent: False):
            QTest.keyClick(self.tab.title_entry, Qt.Key_Escape)
            pump()
        self.assertEqual(self.tab.title_entry.text(), "")


class SignupFlowTest(UiCase):
    """Заявка от Игрока до решения Мастера."""

    def test_player_sends_and_master_confirms(self):
        """Игрок подаёт заявку в окне, Мастер подтверждает в своём окне."""
        frame = self.open_as(self.player, 0)
        showcase = frame.tabs[0]
        showcase.table.select(self.game_id)
        showcase.characters.select(self.hero)
        showcase.on_send()
        pump()
        self.assertEqual(frame.shown, 1)  # открылись «Мои записи»
        rows = signups.list_for_player(self.conn, self.player)
        self.assertEqual([r["status"] for r in rows], ["PENDING"])

        gm_frame = self.open_as(self.gm, 1)
        self.assertIn("(1)", gm_frame.tab_buttons[1].text())
        gm_frame.tabs[1].on_confirm(rows[0]["id"])
        self.assertEqual(
            signups.list_for_player(self.conn, self.player)[0]["status"], "CONFIRMED"
        )

    def test_send_without_character_shows_error(self):
        """Без выбранного персонажа заявка не отправляется."""
        frame = self.open_as(self.player, 0)
        showcase = frame.tabs[0]
        showcase.table.select(self.game_id)
        showcase.on_send()
        self.assertTrue(showcase.error.isVisible())
        self.assertFalse(signups.list_for_player(self.conn, self.player))

    def test_full_game_shows_queue_button(self):
        """Когда мест нет, кнопка называется «Встать в очередь»."""
        other = characters.save_character(
            self.conn, self.player, "Корвин", "Человек", "Волшебник", 2, ""
        )
        auth.register(self.conn, "Игрок Вера", "vera", "1234", "1234", "PLAYER")
        vera = auth.login_user(self.conn, "vera", "1234")
        vera_hero = characters.save_character(
            self.conn, vera, "Миралла", "Тифлинг", "Колдун", 4, ""
        )
        signup = signups.create_signup(self.conn, vera, self.game_id, vera_hero)
        signups.confirm_signup(self.conn, self.gm, signup)
        frame = self.open_as(self.player, 0)
        showcase = frame.tabs[0]
        showcase.table.select(self.game_id)
        self.assertEqual(showcase.send_button.text(), "Встать в очередь")
        self.assertIsNotNone(other)

    def test_character_with_active_signup_cannot_be_deleted(self):
        """Персонажа с активной заявкой удалить нельзя — плашка в форме."""
        signups.create_signup(self.conn, self.player, self.game_id, self.hero)
        frame = self.open_as(self.player, 2)
        tab = frame.tabs[2]
        tab.table.select(self.hero)
        tab.on_delete()
        self.assertTrue(tab.error.isVisible())
        self.assertIsNotNone(characters.get_character(self.conn, self.hero))


class AppTest(UiCase):
    """Тема, крупный текст, выход, обработка ошибок."""

    def test_toggle_theme_and_back(self):
        """Тёмная тема включается и сохраняется, затем возвращается светлая."""
        self.open_as(self.gm, 0)
        self.app.toggle_theme()
        self.assertEqual(theme.THEME, "dark")
        self.assertEqual(settings.get_setting("theme"), "dark")
        self.assertEqual(type(self.app.screen).__name__, "GMFrame")  # кабинет остался
        self.app.toggle_theme()
        self.assertEqual(theme.THEME, "light")

    def test_large_text_all_tabs(self):
        """При крупном тексте все вкладки обеих ролей открываются."""
        settings.write_setting("large_text", True)
        style.apply(qt)
        try:
            for user in (self.gm, self.player):
                self.app.open_main(user)
                for index in range(len(self.app.screen.tabs)):
                    self.app.screen.show_tab(index)
                    pump()
        finally:
            settings.write_setting("large_text", False)
            style.apply(qt)

    def test_logout_returns_to_login(self):
        """«Выйти» открывает окно входа."""
        self.open_as(self.gm, 0)
        self.app.logout()
        self.assertEqual(type(self.app.screen).__name__, "LoginFrame")

    def test_unexpected_error_goes_to_log_and_dialog(self):
        """Непредвиденная ошибка — окно сообщения и запись в журнал."""
        with self.assertLogs("gm_hub", level="ERROR"):
            self.app.show_error(RuntimeError, RuntimeError("сбой"), None)
        self.assertTrue(any("Непредвиденная ошибка" in text for text in self.asked))

    def test_validation_error_is_shown_without_log(self):
        """Ожидаемая ошибка ввода показывается в окне и не пишется в журнал."""
        error = auth.ValidationError("Логин", "Логин занят.")
        self.app.show_error(type(error), error, None)
        self.assertIn("Логин занят.", self.asked)


class MaskedEntryTest(UiCase):
    """Поле даты и времени."""

    def test_digits_get_separators(self):
        """При вводе цифр точки и двоеточие ставятся сами."""
        frame = self.open_as(self.gm, 0)
        tab = frame.tabs[0]
        QTest.keyClicks(tab.date_entry, "27092030")
        QTest.keyClicks(tab.time_entry, "1830")
        self.assertEqual(tab.date_entry.text(), "27.09.2030")
        self.assertEqual(tab.time_entry.text(), "18:30")


if __name__ == "__main__":
    unittest.main()
