-- Server Moderation Session Service schema.
--
-- Postgres runs every file in /docker-entrypoint-initdb.d the first time a
-- container starts with an empty volume, so mounting this folder there is
-- enough to create the tables. It is safe to run again by hand.
--
-- A session is read and written as a whole, so it is one row. The parts that
-- are lists of structured values (the roster, the role assignments, the
-- outcomes Moderation reported and the settled result) are JSONB columns,
-- the same shapes the contract defines.

CREATE TABLE IF NOT EXISTS sessions (
  session_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id                UUID        NOT NULL,
  status                 TEXT        NOT NULL DEFAULT 'lobby'
                                     CHECK (status IN ('lobby', 'active', 'ended')),
  moderator_id           UUID        NOT NULL,
  roster                 JSONB       NOT NULL,
  junior_mods            UUID[]      NOT NULL DEFAULT '{}',
  assignments            JSONB       NOT NULL DEFAULT '[]',
  current_applicant_id   UUID,
  applications_processed INTEGER     NOT NULL DEFAULT 0,
  score                  INTEGER     NOT NULL DEFAULT 0,
  penalties              INTEGER     NOT NULL DEFAULT 0,
  rule_set_version       INTEGER,
  started_at             TIMESTAMPTZ,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcomes               JSONB       NOT NULL DEFAULT '[]',
  result                 JSONB
);
