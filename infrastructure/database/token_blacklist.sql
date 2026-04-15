-- ============================================
-- Token Blacklist Table for JWT Revocation
-- ============================================
-- This table stores revoked JWT tokens to prevent their reuse.
-- Tokens are stored as SHA-256 hashes for security.
-- Expired entries should be periodically cleaned up.

CREATE TABLE IF NOT EXISTS token_blacklist (
  id SERIAL PRIMARY KEY,
  token_hash TEXT NOT NULL,
  revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

-- Index for fast lookup by token hash
CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist(token_hash);

-- Index for cleanup of expired entries
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);

-- Enable Row Level Security
ALTER TABLE token_blacklist ENABLE ROW LEVEL SECURITY;

-- No direct access via PostgREST - managed entirely by API service
-- RLS enabled with no policy = deny all via PostgREST

-- Optional: Create a function to clean up expired tokens
-- Can be called periodically via a cron job or pg_cron extension
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
  DELETE FROM token_blacklist WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
