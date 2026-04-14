-- Users table (replaces auth.ts in-memory Map)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  api_key TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'agent')),
  tier TEXT DEFAULT 'basic',
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
  risk_score NUMERIC NOT NULL DEFAULT 0,
  risk_level TEXT NOT NULL DEFAULT 'low',
  reasons TEXT[] DEFAULT '{}',
  ip_address TEXT,
  user_agent TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  previous_hash TEXT,
  entry_hash TEXT,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_logs(result);

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
