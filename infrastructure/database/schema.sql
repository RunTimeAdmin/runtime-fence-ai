-- =============================================================================
-- Runtime Fence AI - Database Schema
-- =============================================================================
-- MIGRATION STRATEGY:
-- - All tables use CREATE TABLE IF NOT EXISTS for idempotent execution
-- - To add columns to existing tables, use ALTER TABLE ... ADD COLUMN IF NOT EXISTS
-- - NEVER use DROP TABLE in production — use migration scripts for destructive changes
-- - Legacy token-era tables are dropped below (one-time cleanup)
-- =============================================================================

-- Legacy token-era tables (one-time cleanup, safe to remove after first migration)
DROP TABLE IF EXISTS tier_limits CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS token_discounts CASCADE;
DROP TABLE IF EXISTS proposals CASCADE;
DROP TABLE IF EXISTS votes CASCADE;
DROP TABLE IF EXISTS agent_identities CASCADE;

-- ============================================
-- TABLE DEFINITIONS
-- ============================================

-- Users table (replaces auth.ts in-memory Map)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  api_key TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'agent')),
  tier TEXT DEFAULT 'basic' CHECK (tier IN ('basic', 'pro', 'team', 'enterprise')),
  created_at BIGINT NOT NULL,
  updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

-- Rate limits (replaces auth.ts rate limit Map)
CREATE TABLE IF NOT EXISTS rate_limits (
  key TEXT PRIMARY KEY,
  request_count INT NOT NULL DEFAULT 0,
  window_reset_at BIGINT NOT NULL
);

-- User settings (replaces settings.ts Map)
CREATE TABLE IF NOT EXISTS user_settings (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent_id TEXT,
  preset TEXT NOT NULL DEFAULT 'coding',
  blocked_actions TEXT[] DEFAULT '{}',
  blocked_targets TEXT[] DEFAULT '{}',
  spending_limit NUMERIC DEFAULT 0,
  risk_threshold TEXT NOT NULL DEFAULT 'medium' CHECK (risk_threshold IN ('low', 'medium', 'high')),
  auto_kill BOOLEAN DEFAULT TRUE,
  offline_mode BOOLEAN DEFAULT FALSE,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL,
  UNIQUE(user_id, agent_id)
);
CREATE INDEX IF NOT EXISTS idx_settings_user ON user_settings(user_id);

-- Audit logs (replaces audit-logging.ts Array)
CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  timestamp BIGINT NOT NULL,
  user_id TEXT,
  agent_id TEXT,
  action TEXT NOT NULL,
  target TEXT NOT NULL,
  result TEXT NOT NULL CHECK (result IN ('allowed', 'blocked', 'killed')),
  risk_score SMALLINT NOT NULL DEFAULT 0,
  risk_level TEXT NOT NULL DEFAULT 'low',
  reasons TEXT[] DEFAULT '{}',
  ip_address TEXT,
  user_agent TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  previous_hash TEXT,
  entry_hash TEXT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_logs(result);

-- Hash chain enforcement trigger for audit_logs
CREATE OR REPLACE FUNCTION enforce_audit_hash_chain()
RETURNS TRIGGER AS $$
DECLARE
  last_hash TEXT;
BEGIN
  -- entry_hash is required
  IF NEW.entry_hash IS NULL OR NEW.entry_hash = '' THEN
    RAISE EXCEPTION 'audit_logs.entry_hash cannot be null - hash chain integrity required';
  END IF;

  -- Auto-populate previous_hash from the last entry
  SELECT entry_hash INTO last_hash
  FROM audit_logs
  ORDER BY created_at DESC, id DESC
  LIMIT 1;

  NEW.previous_hash := COALESCE(last_hash, 'GENESIS');

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_hash_chain ON audit_logs;
CREATE TRIGGER trg_audit_hash_chain
  BEFORE INSERT ON audit_logs
  FOR EACH ROW
  EXECUTE FUNCTION enforce_audit_hash_chain();

-- Audit requests (replaces index.ts audits Map)
CREATE TABLE IF NOT EXISTS audit_requests (
  id TEXT PRIMARY KEY,
  requester_id TEXT NOT NULL,
  contract_address TEXT NOT NULL,
  audit_type TEXT NOT NULL CHECK (audit_type IN ('basic', 'comprehensive', 'emergency')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'complete', 'failed')),
  results JSONB,
  created_at BIGINT NOT NULL,
  completed_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_audit_req_requester ON audit_requests(requester_id);

-- Usage tracking (replaces usage-tracking.ts Map)
CREATE TABLE IF NOT EXISTS usage_tracking (
  user_id TEXT NOT NULL,
  period_start DATE NOT NULL,
  api_calls_used INT DEFAULT 0,
  updated_at BIGINT NOT NULL,
  PRIMARY KEY (user_id, period_start)
);

-- Agents (for frontend dashboard)
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'killed')),
  last_activity BIGINT,
  api_calls_today INT DEFAULT 0,
  config JSONB DEFAULT '{}'::jsonb,
  created_at BIGINT NOT NULL,
  updated_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_agents_user ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);

-- Kill signals (for admin dashboard)
CREATE TABLE IF NOT EXISTS kill_signals (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  reason TEXT,
  triggered_by TEXT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kills_agent ON kill_signals(agent_id);
CREATE INDEX IF NOT EXISTS idx_kills_created ON kill_signals(created_at DESC);

-- Token blacklist for JWT revocation
CREATE TABLE IF NOT EXISTS token_blacklist (
  id SERIAL PRIMARY KEY,
  token_hash TEXT NOT NULL,
  revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist(token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);

ALTER TABLE token_blacklist ENABLE ROW LEVEL SECURITY;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
-- Enable RLS on all tables. Access is controlled via the
-- Supabase service key used by the API server (bypasses RLS).
-- These policies ensure the PostgREST (anon/authenticated) API
-- cannot read or write data directly without going through
-- the API service.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE kill_signals ENABLE ROW LEVEL SECURITY;

-- Service role policies (API server uses service key which bypasses RLS,
-- but we add explicit policies for the authenticated role used by the frontend)

-- Users: authenticated users can read their own row
CREATE POLICY "Users can view own profile" ON users
  FOR SELECT USING (auth.uid()::text = id);

-- User settings: authenticated users can manage their own settings
CREATE POLICY "Users can manage own settings" ON user_settings
  FOR ALL USING (auth.uid()::text = user_id);

-- Audit logs: authenticated users can read their own logs
CREATE POLICY "Users can view own audit logs" ON audit_logs
  FOR SELECT USING (auth.uid()::text = user_id);

-- Audit requests: authenticated users can manage their own requests
CREATE POLICY "Users can manage own audit requests" ON audit_requests
  FOR ALL USING (auth.uid()::text = requester_id);

-- Usage tracking: authenticated users can view their own usage
CREATE POLICY "Users can view own usage" ON usage_tracking
  FOR SELECT USING (auth.uid()::text = user_id);

-- Agents: authenticated users can manage their own agents
CREATE POLICY "Users can manage own agents" ON agents
  FOR ALL USING (auth.uid()::text = user_id);

-- Kill signals: authenticated users can view kills for their agents
CREATE POLICY "Users can view own kill signals" ON kill_signals
  FOR SELECT USING (
    agent_id IN (SELECT id FROM agents WHERE user_id = auth.uid()::text)
  );

-- Rate limits: no direct access (managed entirely by API service)
-- No policy needed — RLS enabled with no policy = deny all via PostgREST
