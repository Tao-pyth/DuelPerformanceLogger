ALTER TABLE matches ADD COLUMN youtube_flag INTEGER NOT NULL DEFAULT 0;
ALTER TABLE matches ADD COLUMN youtube_video_id TEXT;
ALTER TABLE matches ADD COLUMN youtube_checked_at INTEGER;
CREATE INDEX IF NOT EXISTS idx_matches_youtube_flag ON matches(youtube_flag);
