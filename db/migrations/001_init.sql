CREATE TABLE IF NOT EXISTS db_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    usage_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    start_date TEXT,
    start_time TEXT,
    end_date TEXT,
    end_time TEXT,
    rank_statistics_target INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    usage_count INTEGER NOT NULL DEFAULT 0,
    is_protected INTEGER NOT NULL DEFAULT 0,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_no INTEGER NOT NULL,
    deck_id INTEGER NOT NULL,
    season_id INTEGER,
    turn INTEGER NOT NULL CHECK (turn IN (0, 1)),
    opponent_deck TEXT,
    keywords TEXT,
    memo TEXT NOT NULL DEFAULT '',
    result INTEGER NOT NULL CHECK (result IN (-1, 0, 1)),
    youtube_flag INTEGER NOT NULL DEFAULT 0,
    youtube_url TEXT DEFAULT '',
    youtube_video_id TEXT,
    youtube_checked_at INTEGER,
    favorite INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(deck_id)
        REFERENCES decks(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    FOREIGN KEY(season_id)
        REFERENCES seasons(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS upload_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL UNIQUE,
    recording_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT DEFAULT '',
    youtube_url TEXT DEFAULT '',
    youtube_video_id TEXT DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(match_id)
        REFERENCES matches(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_upload_jobs_match_id ON upload_jobs(match_id);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_status ON upload_jobs(status);

