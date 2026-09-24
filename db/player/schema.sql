-- Player Service schema.
--
-- Postgres runs every file in /docker-entrypoint-initdb.d the first time a
-- container starts with an empty volume, so mounting this folder there is
-- enough to create the tables. It is safe to run again by hand.

CREATE TABLE IF NOT EXISTS players (
  player_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  username             TEXT        NOT NULL,
  email                TEXT        NOT NULL UNIQUE,
  password_hash        TEXT        NOT NULL,
  level                INTEGER     NOT NULL DEFAULT 1,
  xp                   INTEGER     NOT NULL DEFAULT 0,
  display_name         TEXT,
  avatar               TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Progression, applied when a SessionCompleted event arrives.
  completed_shifts     INTEGER     NOT NULL DEFAULT 0,
  disciplinary_actions INTEGER     NOT NULL DEFAULT 0
);

-- For a database created before these columns existed.
ALTER TABLE players ADD COLUMN IF NOT EXISTS completed_shifts     INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ADD COLUMN IF NOT EXISTS disciplinary_actions INTEGER NOT NULL DEFAULT 0;

-- Refresh tokens are stored by the SHA-256 of the token, never the token
-- itself, and are deleted when their player is.
CREATE TABLE IF NOT EXISTS refresh_tokens (
  token_hash TEXT        PRIMARY KEY,
  player_id  UUID        NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS refresh_tokens_player_id_idx ON refresh_tokens (player_id);

-- One row per friendship, held once rather than once per direction. The row
-- remembers who asked, which is what makes a request acceptable.
CREATE TABLE IF NOT EXISTS friendships (
  requester_id UUID        NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
  addressee_id UUID        NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
  status       TEXT        NOT NULL CHECK (status IN ('pending', 'accepted')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (requester_id, addressee_id),
  CHECK (requester_id <> addressee_id)
);

-- A pair may appear only once, whichever of the two asked first. This is what
-- stops two players who request each other at the same moment from ending up
-- with two friendships.
CREATE UNIQUE INDEX IF NOT EXISTS friendships_pair_idx
  ON friendships (LEAST(requester_id, addressee_id), GREATEST(requester_id, addressee_id));

-- A moderation team. Shifts are opened from here, which is why the roster
-- Session receives is built from this table.
CREATE TABLE IF NOT EXISTS teams (
  team_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT        NOT NULL,
  owner_id   UUID        NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS team_members (
  team_id   UUID        NOT NULL REFERENCES teams (team_id) ON DELETE CASCADE,
  player_id UUID        NOT NULL REFERENCES players (player_id) ON DELETE CASCADE,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (team_id, player_id)
);

CREATE INDEX IF NOT EXISTS team_members_player_id_idx ON team_members (player_id);

-- Every event this service has already applied. The contract requires
-- consumers to be idempotent on eventId, so a redelivery never awards the
-- same XP twice.
CREATE TABLE IF NOT EXISTS processed_events (
  event_id     UUID        PRIMARY KEY,
  type         TEXT        NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
