-- Структура БД АС «GM Hub» по приложению А технического задания.
-- Даты хранятся строкой в формате ГГГГ-ММ-ДД ЧЧ:ММ (п. 4.3.2 ТЗ).

CREATE TABLE IF NOT EXISTS Users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT    NOT NULL,
    login         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('GM', 'PLAYER')),
    created_at    TEXT    NOT NULL,
    -- когда Игрок последний раз открывал «Мои записи» (для отметки новых решений)
    signups_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS Characters (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES Users (id),
    name      TEXT    NOT NULL,
    race      TEXT,
    class     TEXT,
    level     INTEGER NOT NULL CHECK (level BETWEEN 1 AND 20),
    backstory TEXT
);

CREATE TABLE IF NOT EXISTS Games (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    gm_id        INTEGER NOT NULL REFERENCES Users (id),
    title        TEXT    NOT NULL,
    description  TEXT,
    scheduled_at TEXT    NOT NULL,
    max_players  INTEGER NOT NULL CHECK (max_players > 0),
    status       TEXT    NOT NULL DEFAULT 'PLANNED'
                         CHECK (status IN ('PLANNED', 'CLOSED', 'CANCELLED')),
    summary      TEXT,  -- итоги прошедшей сессии, их видят Игроки
    levels_given INTEGER NOT NULL DEFAULT 0  -- 1 — уровни участникам уже повышены
);

CREATE TABLE IF NOT EXISTS Game_Signups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id      INTEGER NOT NULL REFERENCES Games (id),
    character_id INTEGER NOT NULL REFERENCES Characters (id),
    status       TEXT    NOT NULL DEFAULT 'PENDING'
                         CHECK (status IN ('PENDING', 'CONFIRMED', 'REJECTED')),
    comment      TEXT,
    created_at   TEXT    NOT NULL,
    decided_at   TEXT,
    reason       TEXT,  -- причина отказа (пишет Мастер или «Сессия отменена»)
    -- один персонаж не может дважды подать заявку на одну сессию (п. 4.1.4)
    UNIQUE (game_id, character_id)
);

CREATE TABLE IF NOT EXISTS Game_Notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id    INTEGER NOT NULL UNIQUE REFERENCES Games (id),
    content    TEXT,
    updated_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS World_Notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    -- у каждого Мастера своя база мира
    gm_id      INTEGER NOT NULL REFERENCES Users (id),
    category   TEXT    NOT NULL CHECK (category IN ('LORE', 'NPC', 'LOCATION')),
    title      TEXT    NOT NULL,
    content    TEXT,
    updated_at TEXT    NOT NULL
);
