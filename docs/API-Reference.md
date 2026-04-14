# API Reference

Complete REST API documentation for $KILLSWITCH.

**Base URL:** `https://api.runtimefence.com` (production) or `http://localhost:3001` (development)

---

## Authentication

All endpoints except `/api/auth/*` require authentication.

### JWT Token (Recommended)

```bash
curl -X POST https://api.runtimefence.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your_password"}'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "tier": "pro"
  }
}
```

**Use the token:**
```bash
curl -H "Authorization: Bearer <token>" https://api.runtimefence.com/api/runtime/status
```

### API Key

```bash
curl -H "X-API-Key: ks_live_xxxxx" https://api.runtimefence.com/api/runtime/status
```

---

## Endpoints

### Runtime Assessment

#### POST /api/runtime/assess

Validate an action before execution.

**Request:**
```json
{
  "agent_id": "my-agent-123",
  "action": "file_write",
  "target": "/etc/passwd",
  "metadata": {
    "cost": 0,
    "context": "Attempting to modify system file"
  }
}
```

**Response (Blocked):**
```json
{
  "allowed": false,
  "risk_score": 95,
  "reasons": [
    "Target '/etc/passwd' is protected",
    "Action 'file_write' to system files is blocked"
  ],
  "action_id": "act_abc123",
  "timestamp": "2026-02-01T22:30:00Z"
}
```

**Response (Allowed):**
```json
{
  "allowed": true,
  "risk_score": 15,
  "reasons": [],
  "action_id": "act_def456",
  "timestamp": "2026-02-01T22:30:00Z"
}
```

---

#### POST /api/runtime/kill

Emergency kill switch - instantly revokes agent credentials.

**Request:**
```json
{
  "agent_id": "my-agent-123",
  "reason": "Suspicious behavior detected",
  "scope": "agent"
}
```

**Scope Options:**
- `agent` - Kill specific agent only
- `wallet` - Kill all agents for wallet
- `all` - Emergency kill all (admin only)

**Response:**
```json
{
  "success": true,
  "killed_at": "2026-02-01T22:30:00Z",
  "agent_id": "my-agent-123",
  "spiffe_id": "spiffe://killswitch.ai/agent/my-agent-123",
  "revocation_propagation_ms": 28
}
```

---

#### GET /api/runtime/status

Get current fence status for an agent.

**Query Parameters:**
- `agent_id` (required) - Agent identifier

**Response:**
```json
{
  "agent_id": "my-agent-123",
  "status": "active",
  "spiffe_id": "spiffe://killswitch.ai/agent/my-agent-123",
  "created_at": "2026-02-01T20:00:00Z",
  "last_action": "2026-02-01T22:29:00Z",
  "stats": {
    "total_actions": 150,
    "blocked_actions": 3,
    "avg_risk_score": 22
  },
  "thresholds": {
    "file_read": "45/100 per minute",
    "network_request": "12/50 per minute",
    "shell_exec": "0/10 per 5 minutes"
  }
}
```

---

### Agent Management

#### POST /api/agents/register

Register a new agent with SPIFFE identity.

**Request:**
```json
{
  "name": "my-agent",
  "type": "autonomous",
  "wallet_address": "0x...",
  "metadata": {
    "framework": "langchain",
    "version": "0.1.0"
  }
}
```

**Response:**
```json
{
  "agent_id": "my-agent-123",
  "spiffe_id": "spiffe://killswitch.ai/agent/my-agent-123",
  "api_key": "ks_agent_xxxxx",
  "svid": {
    "cert": "-----BEGIN CERTIFICATE-----...",
    "expires_at": "2026-02-01T23:30:00Z"
  }
}
```

---

#### GET /api/agents

List all agents for authenticated user.

**Response:**
```json
{
  "agents": [
    {
      "agent_id": "my-agent-123",
      "name": "my-agent",
      "status": "active",
      "last_seen": "2026-02-01T22:29:00Z"
    }
  ],
  "total": 1
}
```

---

#### DELETE /api/agents/:agent_id

Permanently delete an agent and revoke credentials.

**Response:**
```json
{
  "success": true,
  "agent_id": "my-agent-123",
  "deleted_at": "2026-02-01T22:30:00Z"
}
```

---

### Settings

#### GET /api/settings

Get current fence settings.

**Response:**
```json
{
  "blocked_actions": ["delete", "exec", "sudo", "rm"],
  "blocked_targets": [".env", "production", "wallet", "/etc/*"],
  "spending_limit": 100.0,
  "risk_threshold": 80,
  "auto_kill_enabled": true,
  "auto_kill_threshold": 90,
  "fail_mode": "CLOSED",
  "alerts": {
    "email_enabled": true,
    "sms_enabled": false,
    "slack_enabled": true
  }
}
```

---

#### POST /api/settings

Update fence settings.

**Request:**
```json
{
  "blocked_actions": ["delete", "exec", "sudo", "rm", "wget"],
  "spending_limit": 50.0,
  "auto_kill_threshold": 85
}
```

**Response:**
```json
{
  "success": true,
  "updated_at": "2026-02-01T22:30:00Z"
}
```

---

### Audit Logs

#### GET /api/audit-logs

Get audit logs with filtering.

**Query Parameters:**
- `agent_id` - Filter by agent
- `action` - Filter by action type
- `allowed` - Filter by allowed (true/false)
- `from` - Start timestamp (ISO 8601)
- `to` - End timestamp (ISO 8601)
- `limit` - Max results (default: 100, max: 1000)
- `offset` - Pagination offset

**Response:**
```json
{
  "logs": [
    {
      "id": "log_abc123",
      "agent_id": "my-agent-123",
      "action": "file_write",
      "target": "/etc/passwd",
      "allowed": false,
      "risk_score": 95,
      "reasons": ["Target is protected"],
      "timestamp": "2026-02-01T22:30:00Z",
      "hash": "sha256:abc123...",
      "prev_hash": "sha256:def456..."
    }
  ],
  "total": 150,
  "has_more": true
}
```

---

### Governance

#### GET /api/governance/proposals

List active governance proposals.

**Response:**
```json
{
  "proposals": [
    {
      "id": "prop_123",
      "title": "Add new blocked action: fork_bomb",
      "description": "Proposal to block fork bomb attacks",
      "proposer": "0x...",
      "status": "active",
      "votes_for": 1500000,
      "votes_against": 200000,
      "quorum": 1000000,
      "ends_at": "2026-02-08T00:00:00Z"
    }
  ]
}
```

---

#### POST /api/governance/vote

Cast a vote on a proposal.

**Request:**
```json
{
  "proposal_id": "prop_123",
  "vote": "for",
  "voting_power": 10000
}
```

**Response:**
```json
{
  "success": true,
  "proposal_id": "prop_123",
  "vote": "for",
  "voting_power": 10000,
  "tx_hash": "0x..."
}
```

---

### Subscriptions

#### GET /api/subscription

Get current subscription status.

**Response:**
```json
{
  "tier": "pro",
  "status": "active",
  "limits": {
    "agents": 10,
    "actions_per_day": 10000,
    "audit_retention_days": 90
  },
  "usage": {
    "agents": 3,
    "actions_today": 1542
  },
  "renewal_date": "2026-03-01",
  "token_discount": 10
}
```

---

#### POST /api/subscription/upgrade

Upgrade subscription tier.

**Request:**
```json
{
  "tier": "team",
  "payment_method": "stripe",
  "coupon_code": "LAUNCH20"
}
```

---

### Token Holdings

#### GET /api/token/holdings

Get $KILLSWITCH token balance and benefits.

**Query Parameters:**
- `wallet_address` (required)

**Response:**
```json
{
  "wallet_address": "0x...",
  "balance": 150000,
  "tier": "gold",
  "benefits": {
    "discount_percent": 20,
    "voting_power": 150000,
    "governance_access": true
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing or invalid auth |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Rate Limited - Too many requests |
| 500 | Server Error - Internal error |

**Error Response Format:**
```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent with ID 'xyz' not found",
    "details": {}
  }
}
```

---

## Rate Limits

| Tier | Requests/min | Actions/day |
|------|--------------|-------------|
| Free | 10 | 100 |
| Basic | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Team | 600 | 50,000 |
| Enterprise | 1,200 | Unlimited |

---

## Webhooks

Configure webhooks at `/settings` to receive real-time events.

**Event Types:**
- `agent.killed` - Agent was killed
- `action.blocked` - Action was blocked
- `threshold.exceeded` - Behavioral threshold exceeded
- `anomaly.detected` - Anomaly score > 90

**Payload:**
```json
{
  "event": "action.blocked",
  "timestamp": "2026-02-01T22:30:00Z",
  "data": {
    "agent_id": "my-agent-123",
    "action": "file_write",
    "target": "/etc/passwd",
    "risk_score": 95
  }
}
```

---

## SDK Examples

### Python

```python
from killswitch import Client

client = Client(api_key="ks_live_xxxxx")

# Validate action
result = client.assess("file_write", "/etc/passwd")
if not result.allowed:
    print(f"Blocked: {result.reasons}")

# Kill agent
client.kill("my-agent-123", reason="Emergency")

# Get status
status = client.status("my-agent-123")
print(f"Risk score: {status.avg_risk_score}")
```

### TypeScript

```typescript
import { KillSwitch } from '@killswitch/sdk';

const client = new KillSwitch({ apiKey: 'ks_live_xxxxx' });

// Validate action
const result = await client.assess('file_write', '/etc/passwd');
if (!result.allowed) {
  console.log('Blocked:', result.reasons);
}

// Kill agent
await client.kill('my-agent-123', { reason: 'Emergency' });
```

---

## Related Documentation

- [Integration Guide](Integration-Guide.md)
- [Troubleshooting & FAQ](Troubleshooting-FAQ.md)
- [Security Hardening](Security-Hardening.md)
