# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-04-16

### Added
- SPIFFE/SPIRE Workload API integration for agent identity verification
- Distributed kill propagation via WebSocket pub/sub (<30s SLA)
- Immutable hash-chained audit logs with optional S3 export
- Audit chain verification endpoint (`/api/audit/verify`)
- Rate limiting in `RuntimeFence.validate()` (self-DoS prevention)
- Async sentence-transformers model preloading
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- OWASP Top 10 for LLM Applications security mapping

### Changed
- Security modules (behavioral, intent, sliding_window) now wired into `validate()` flow
- Process kill uses `os.killpg()` for process-group termination
- Network kill adds `atexit` cleanup handler
- Breach callbacks debounced (60s cooldown)
- Behavioral thresholds persisted via SQLite

## [1.1.0] - 2025-04-14

### Added
- Kill state persistence to Supabase with startup restore
- Tenant isolation on kill/reset endpoints
- JWT refresh (`/api/auth/refresh`) and revocation (`/api/auth/revoke`) endpoints
- Token blacklist table with Supabase persistence
- Supabase-backed rate limiting with in-memory fallback
- SupabaseVoteProvider for real governance voting
- Governance tables (proposals, votes) with RLS
- Sentence-transformers optional dependency for drift detection
- `freeze_hashes.py` CI/CD script for build-time hash freezing
- `FailModeHandler` integration (CLOSED/CACHED/OPEN strategy)
- Encrypted policy cache with system-level path
- NET_ADMIN capability check on startup

### Fixed
- JWT hardcoded fallback secret removed (hard exit if missing)
- `Math.random()` replaced with `crypto.randomBytes()` for API keys
- `EMBEDDED_CRITICAL_HASHES` populated via `_compute_critical_hashes()`
- `verify_self()` performs actual hash comparison (was always True)
- HMAC uses proper `hmac.new()` (was vulnerable string concatenation)
- `__builtins__` replaced with `import builtins` for cross-platform reliability
- MD5 cache keys replaced with SHA-256
- `--pid-owner` replaced with `--uid-owner` (kernel 3.14+ compatible)
- macOS pf uses per-user anchor rules (was blocking globally)
- AWS SG blocking replaces instance SGs (was only adding)
- `fence_proxy.py` implements real CONNECT tunneling (was fake 200)
- RiskLevel.HIGH threshold fixed to 70 (was 75)
- LLM risk scores floor-bound by intent category
- `sliding_window._total` clamped to prevent negative values
- DNS tunneling detection uses Shannon entropy + CDN whitelist
- ExfiltrationDetector uses time-windowed eviction
- Breach history bounded to deque(maxlen=1000)
- LLM JSON parsing handles nested braces and markdown fences
- `reset()` requires reason parameter and optional auth token

### Removed
- All Solana token economics (SOLANA_RPC_URL, governance, staking)
- False Solidity contract claims
- `contracts/` directory
- Orphaned environment variables

## [1.0.0] - 2025-04-12

### Added
- Initial release of Runtime Fence AI
- Core `RuntimeFence` Python class with decorator pattern
- 10 security hardening modules
- TypeScript kill switch engine
- Express REST API with JWT authentication
- Next.js dashboard
- Supabase schema with RLS
- SPIFFE-inspired identity patterns
- Comprehensive documentation and wiki
