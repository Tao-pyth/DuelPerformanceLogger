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

CREATE UNIQUE INDEX IF NOT EXISTS idx_upload_jobs_match_id
    ON upload_jobs(match_id);

CREATE INDEX IF NOT EXISTS idx_upload_jobs_status
    ON upload_jobs(status);
