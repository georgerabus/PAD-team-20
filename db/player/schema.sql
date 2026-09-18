-- Player Service schema.
--
-- Postgres runs every file in /docker-entrypoint-initdb.d the first time a
-- container starts with an empty volume, so mounting this folder there is
-- enough to create the tables. It is safe to run again by hand.

CREATE TABLE IF NOT EXISTS players (
  player_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  username      TEXT        NOT NULL,
  email         TEXT        NOT NULL UNIQUE,
  password_hash TEXT        NOT NULL,
  level         INTEGER     NOT NULL DEFAULT 1,
  xp            INTEGER     NOT NULL DEFAULT 0,
  display_name  TEXT,
  avatar        TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Refresh tokens are stored by the SHA-256 of the token, never the token
-- itself, and are deleted when their player is.
CREATE TABLE IF NOT EXISTS refresh_tokens (
  token_hash TEXT        PRIMARY KEY,
  player_id  UUID        NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS refresh_tokens_player_id_idx ON refresh_tokens (player_id);
