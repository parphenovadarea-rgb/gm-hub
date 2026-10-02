# Game Master Hub

Ассистент ведущего настольных ролевых игр: расписание сессий, запись игроков,
сюжетный блокнот Мастера. Учебная практика УП.01, группа ИСП-34.

**Стек:** Python 3.10+, SQLite (`sqlite3`), Tkinter/ttk, `hashlib`.

## Структура

```
gm_hub/
  config.py        настройки (путь к БД, формат дат)
  db/              уровень данных
    schema.sql     6 таблиц по приложению А ТЗ
    connection.py  подключение, PRAGMA foreign_keys = ON
  logic/           уровень бизнес-логики
    errors.py      исключения с текстом для пользователя
    auth.py        регистрация и вход, SHA-256 с солью
  ui/              уровень представления (дни 10–12)
tests/             тесты по сценариям п. 6.1 ТЗ
main.py            точка входа
```

## Запуск

```
python main.py
python -m unittest -v
```

## Инструменты разработки

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install
black .
flake8
```

## Ветки

Feature Branch Workflow: `main` содержит только рабочий код, каждая функция
делается в своей ветке `feature/<название>` и попадает в `main` через Pull Request.
