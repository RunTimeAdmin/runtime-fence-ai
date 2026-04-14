# SPIFFE Integration

The $KILLSWITCH Protocol uses SPIFFE (Secure Production Identity Framework For Everyone) patterns to provide cryptographic identity for AI agents.

## Why SPIFFE?

| Traditional (API Keys) | $KILLSWITCH (SPIFFE) |
|------------------------|----------------------|
| Shared secrets | Unique identity per agent |
| 24-hour revocation | <30 second kill |
| "Some agent accessed X" | "Agent-7 accessed X at Y" |
| Manual rotation | Auto-rotating (5 min) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    $KILLSWITCH STACK                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: ECONOMICS ($KILLSWITCH Token)                     │
│  • Hold tokens → Get subscription discounts                 │
│  • Hold tokens → Vote on kill policies                      │
│  • Economic skin in the game = better behavior              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: IDENTITY (SPIFFE)                                 │
│  • Each agent: unique cryptographic identity                │
│  • Auto-rotating credentials (no static keys)               │
│  • Instant revocation = instant kill                        │
│  • Immutable audit trail with SPIFFE IDs                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: SAFETY (Runtime Fence)                            │
│  • Monitor agent actions in real-time                       │
│  • Circuit breaker auto-kill on anomalies                   │
│  • Rate limiting and boundary enforcement                   │
│  • Safe resume after kill                                   │
└─────────────────────────────────────────────────────────────┘
```

## SPIFFE ID Format

```
spiffe://killswitch.ai/{agent-type}/{agent-id}

Examples:
spiffe://killswitch.ai/agent/7b3a5f2e-1234-5678-9abc-def012345678
spiffe://killswitch.ai/admin/panel-controller
spiffe://killswitch.ai/governance/voting-contract
```

## Key Components

### 1. Identity Service
- Registers agents with unique SPIFFE IDs
- Issues SVIDs (SPIFFE Verifiable Identity Documents)
- Auto-rotates credentials every 5 minutes
- Location: `src/lib/spiffe/identity-service.ts`

### 2. Kill API
- `POST /api/kill` - Kill single agent
- `POST /api/kill/emergency` - Kill all agents for wallet
- Revokes SPIFFE ID = instant termination
- Location: `app/api/kill/route.ts`

### 3. Circuit Breaker
- Auto-kills on 10 consecutive failures
- Auto-kills on 80% error rate
- Auto-kills on anomaly score > 90
- Location: `src/lib/spiffe/circuit-breaker.ts`

### 4. Audit Logger
- Immutable logs with SHA-256 hash chain
- Every action tied to SPIFFE ID
- Tamper-proof for compliance
- Location: `src/lib/spiffe/circuit-breaker.ts`

## Database Schema

### agent_identities
| Column | Type | Description |
|--------|------|-------------|
| spiffe_id | TEXT | Unique identity |
| agent_id | UUID | Agent UUID |
| wallet_address | TEXT | Owner's wallet |
| status | TEXT | active/revoked/expired |
| expires_at | TIMESTAMPTZ | Credential expiry |

### kill_signals
| Column | Type | Description |
|--------|------|-------------|
| spiffe_id | TEXT | Target agent |
| signal_type | TEXT | immediate_termination |
| reason | TEXT | Kill reason |
| broadcast_at | TIMESTAMPTZ | Signal time |

## Kill Flow

```
1. User clicks KILL in dashboard
        ↓
2. POST /api/kill { spiffeId, reason }
        ↓
3. Update agent_identities SET status = 'revoked'
        ↓
4. Insert into kill_signals (broadcast)
        ↓
5. Supabase Realtime notifies all services
        ↓
6. Services reject agent's requests
        ↓
7. Agent loses all access (<30 seconds)
```

## Competitive Advantage

| Feature | $KILLSWITCH | OpenAI | AWS | 1Password |
|---------|-------------|--------|-----|-----------|
| Identity | Unique SPIFFE ID | Shared API key | IAM role | Vault |
| Kill Speed | <30 seconds | 24+ hours | Manual | Hours |
| Audit | Hash-chained | Basic logs | CloudTrail | Vault logs |
| Auto-Kill | Circuit breaker | None | None | None |

## Related Pages

- [[Home]]
- [[API-Reference]]
- [[Enterprise-Edition]]
- [[Token-Utility]]
