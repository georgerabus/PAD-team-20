-- Moderation Service schema.
--
-- Postgres runs every file in /docker-entrypoint-initdb.d the first time a
-- container starts with an empty volume, so mounting this folder there is
-- enough to create the tables. It is safe to run again by hand.

-- One decision per applicant: the log Session reads at shift end.
CREATE TABLE IF NOT EXISTS decisions (
  decision_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       UUID        NOT NULL,
  applicant_id     UUID        NOT NULL UNIQUE,
  moderator_id     UUID        NOT NULL,
  action           TEXT        NOT NULL CHECK (action IN ('accept', 'reject', 'flag', 'ban')),
  correct          BOOLEAN     NOT NULL,
  violated_rules   JSONB       NOT NULL DEFAULT '[]',
  penalty          INTEGER     NOT NULL CHECK (penalty >= 0),
  outcome          TEXT        NOT NULL
                               CHECK (outcome IN ('correct', 'wrong_admit', 'wrong_reject', 'missed_ban')),
  rule_set_version INTEGER     NOT NULL,
  decided_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS decisions_session_id_idx ON decisions (session_id, decided_at);

-- The current ruleSetVersion per session, from the last RulesUpdated.
CREATE TABLE IF NOT EXISTS session_rule_sets (
  session_id       UUID        PRIMARY KEY,
  rule_set_version INTEGER     NOT NULL,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- eventIds already applied, so a redelivered event is skipped.
CREATE TABLE IF NOT EXISTS processed_events (
  event_id     UUID        PRIMARY KEY,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
