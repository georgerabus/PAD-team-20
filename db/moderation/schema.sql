-- Moderation Service schema.
--
-- Postgres runs every file in /docker-entrypoint-initdb.d the first time a
-- container starts with an empty volume, so mounting this folder there is
-- enough to create the tables. It is safe to run again by hand.

CREATE TABLE IF NOT EXISTS decisions (
  decision_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     UUID        NOT NULL,
  applicant_id   UUID        NOT NULL,
  moderator_id   UUID        NOT NULL,
  action         TEXT        NOT NULL CHECK (action IN ('accept', 'reject', 'flag', 'ban')),
  correct        BOOLEAN     NOT NULL DEFAULT false,
  violated_rules JSONB       NOT NULL DEFAULT '[]',
  penalty        INTEGER     NOT NULL DEFAULT 0,
  outcome        TEXT        NOT NULL DEFAULT 'correct'
                             CHECK (outcome IN ('correct', 'wrong_admit', 'wrong_reject', 'missed_ban')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
