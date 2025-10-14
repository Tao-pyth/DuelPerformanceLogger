PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE matches_new (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  match_no    INTEGER NOT NULL,
  deck_id     INTEGER NOT NULL,
  turn        INTEGER NOT NULL CHECK (turn IN (0,1)),
  opponent_deck TEXT,
  keywords    TEXT,
  result      INTEGER NOT NULL CHECK (result IN (-1,0,1)),
  created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

INSERT INTO matches_new (id, match_no, deck_id, turn, opponent_deck, keywords, result, created_at)
SELECT
  m.id,
  m.match_no,
  (SELECT d.id FROM decks d WHERE d.name = m.deck_name),
  m.turn,
  m.opponent_deck,
  m.keywords,
  m.result,
  m.created_at
FROM matches m;

SELECT CASE WHEN EXISTS(SELECT 1 FROM matches_new WHERE deck_id IS NULL)
            THEN RAISE(ABORT, 'deck_id resolution failed (unknown deck_name)')
       END;

DROP TABLE matches;
ALTER TABLE matches_new RENAME TO matches;

CREATE INDEX IF NOT EXISTS idx_matches_deck_id ON matches(deck_id);
CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at);
CREATE INDEX IF NOT EXISTS idx_matches_result ON matches(result);

COMMIT;
PRAGMA foreign_keys = ON;
