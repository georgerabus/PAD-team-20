-- Discord DMs Service schema.
--
-- Postgres runs every file in /docker-entrypoint-initdb.d the first time a
-- container starts with an empty volume, so mounting this folder there is
-- enough to create the tables. It is safe to run again by hand.

CREATE TABLE IF NOT EXISTS channels (
  channel_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID        NOT NULL,
  name       TEXT        NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  message_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id UUID        NOT NULL REFERENCES channels (channel_id) ON DELETE CASCADE,
  author_id  UUID        NOT NULL,
  content    TEXT,
  attachment JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT messages_content_or_attachment CHECK (content IS NOT NULL OR attachment IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS messages_channel_id_idx ON messages (channel_id);
