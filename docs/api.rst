Программный интерфейс (API)
===========================

Сетевого API у приложения нет — оно настольное. Роль внутреннего API между
интерфейсом и логикой выполняют функции модулей ``gm_hub.logic``: они получают
подключение к БД и текущего пользователя, проверяют права и данные и возвращают
результат или вызывают ``ValidationError`` / ``AccessError``.

Описание ниже собирается автоматически из docstrings исходного кода
(``sphinx.ext.autodoc``).

Общие модули
------------

.. automodule:: gm_hub.config
   :members:

.. automodule:: gm_hub.settings
   :members:

Уровень данных
--------------

.. automodule:: gm_hub.db.database
   :members:

Бизнес-логика
-------------

Ошибки
~~~~~~

.. automodule:: gm_hub.logic.errors
   :members:

Пользователи
~~~~~~~~~~~~

.. automodule:: gm_hub.logic.auth
   :members:

Игровые сессии
~~~~~~~~~~~~~~

.. automodule:: gm_hub.logic.games
   :members:

Заявки
~~~~~~

.. automodule:: gm_hub.logic.signups
   :members:

Персонажи
~~~~~~~~~

.. automodule:: gm_hub.logic.characters
   :members:

Заметки и база мира
~~~~~~~~~~~~~~~~~~~

.. automodule:: gm_hub.logic.notes
   :members:

Календарь и кубики
~~~~~~~~~~~~~~~~~~

.. automodule:: gm_hub.logic.month
   :members:

.. automodule:: gm_hub.logic.dice
   :members:

Интерфейс
---------

Главное окно и оформление
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: gm_hub.ui.app
   :members:

.. automodule:: gm_hub.ui.theme
   :members:

.. automodule:: gm_hub.ui.style
   :members:

Общие элементы
~~~~~~~~~~~~~~

.. automodule:: gm_hub.ui.common
   :members:

.. automodule:: gm_hub.ui.table
   :members:

.. automodule:: gm_hub.ui.mask
   :members:

Окна
~~~~

.. automodule:: gm_hub.ui.auth_windows
   :members:

.. automodule:: gm_hub.ui.gm_window
   :members:

.. automodule:: gm_hub.ui.player_window
   :members:

.. automodule:: gm_hub.ui.profile_window
   :members:

.. automodule:: gm_hub.ui.help_window
   :members:
