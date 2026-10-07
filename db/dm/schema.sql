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
  CONSTRAINT channels_session_name_key UNIQUE (session_id, name)
);

-- A message carries text or a shared attachment, never both.
CREATE TABLE IF NOT EXISTS messages (
  message_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id UUID        NOT NULL REFERENCES channels (channel_id) ON DELETE CASCADE,
  author_id  UUID        NOT NULL,
  content    TEXT,
  attachment JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT messages_content_xor_attachment CHECK ((content IS NULL) <> (attachment IS NULL))
);

CREATE INDEX IF NOT EXISTS messages_channel_page_idx ON messages (channel_id, created_at DESC, message_id DESC);
