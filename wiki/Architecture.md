# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RUNTIME FENCE PROTOCOL                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LAYER 2: SPIFFE IDENTITY                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Unique ID   │  │ Auto-Rotate │  │ Instant     │  │ Immutable  │ │   │
│  │  │ Per Agent   │  │ Credentials │  │ Revocation  │  │ Audit Logs │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LAYER 1: RUNTIME FENCE                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Action      │  │ Risk        │  │ Circuit     │  │ Kill       │ │   │
│  │  │ Monitoring  │  │ Scoring     │  │ Breaker     │  │ Switch     │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   AI Agent   │────▶│  Runtime     │────▶│   Target     │
│              │     │  Fence       │     │   Service    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       │                    ▼                    │
       │           ┌──────────────┐              │
       │           │  Risk Score  │              │
       │           │  (0-100)     │              │
       │           └──────────────┘              │
       │                    │                    │
       │         ┌──────────┴──────────┐        │
       │         ▼                     ▼        │
       │  ┌────────────┐       ┌────────────┐   │
       │  │  ALLOW     │       │  BLOCK     │   │
       │  │  (score<70)│       │  (score≥70)│   │
       │  └────────────┘       └────────────┘   │
       │                              │         │
       │                              ▼         │
       │                    ┌──────────────┐    │
       │                    │  Kill Switch │    │
       │                    │  (if needed) │    │
       │                    └──────────────┘    │
       │                              │         │
       ▼                              ▼         ▼
┌─────────────────────────────────────────────────────┐
│                    AUDIT LOG                         │
│  [SPIFFE ID] [Action] [Risk Score] [Result] [Time]  │
└─────────────────────────────────────────────────────┘
```

## Kill Switch Flow

```
┌─────────────┐
│  Dashboard  │
│  KILL btn   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ POST /api/kill  │
│ { spiffeId,     │
│   reason }      │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Supabase            │
│ agent_identities    │
│ status = 'revoked'  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Supabase            │
│ kill_signals        │
│ (real-time)         │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ All Services        │◀──── Subscribed to kill_signals
│ Reject Agent        │
└─────────────────────┘
          │
          ▼
    ┌───────────┐
    │  Agent    │
    │  KILLED   │
    │  (<30s)   │
    └───────────┘
```

## Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
├────────────────────────────────────────────────────────────────┤
│  /                    Landing page                              │
│  /agents              Agent dashboard + kill controls           │
│  /subscription        Pricing + tier management                 │

│  /admin               Metrics + user management                 │
└────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                        API LAYER (Next.js)                      │
├────────────────────────────────────────────────────────────────┤
│  /api/auth            Wallet-based JWT auth                     │
│  /api/kill            SPIFFE revocation endpoint                │
│  /api/health          System status                             │

└────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                        SERVICES                                 │
├────────────────────────────────────────────────────────────────┤
│  SpiffeIdentityService    Agent registration + SVID issuance   │
│  CircuitBreaker           Auto-kill on anomalies               │
│  ImmutableAuditLogger     Hash-chained audit trail             │
│  useAuth                  Session management                   │
└────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────┐
│                        DATABASE (Supabase)                      │
├────────────────────────────────────────────────────────────────┤
│  users                 Wallet addresses + tiers                 │
│  agent_identities      SPIFFE registry                          │
│  kill_signals          Real-time broadcast                      │
│  audit_logs            Immutable trail                          │

│  subscriptions         Stripe + crypto payments                 │
└────────────────────────────────────────────────────────────────┘
                                │
                                ▼
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AUTHENTICATION                                      │   │
│  │  • Phantom wallet signature                          │   │
│  │  • JWT tokens (7-day expiry)                         │   │
│  │  • SPIFFE IDs for agents                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AUTHORIZATION                                       │   │
│  │  • SPIFFE ID → permissions mapping                   │   │
│  │  • RLS policies in Supabase                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MONITORING                                          │   │
│  │  • Circuit breaker (failure detection)              │   │
│  │  • Anomaly scoring                                   │   │
│  │  • Rate limiting                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ENFORCEMENT                                         │   │
│  │  • Instant kill via SPIFFE revocation               │   │
│  │  • Real-time broadcast to all services              │   │
│  │  • Immutable audit logging                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Related Pages

- [[Home]]
- [[SPIFFE-Integration]]
- [[Enterprise-Edition]]
- [[API-Reference]]
