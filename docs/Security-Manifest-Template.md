# AI Agent Security Manifest Template

**Version:** 1.0  
**Protocol:** $KILLSWITCH  
**Identity Provider:** SPIFFE/SPIRE

---

## Overview

The Security Manifest is the contract between an agent owner and the $KILLSWITCH network. It defines exactly what "normal" looks like so Staked Oracles can detect "broken" and execute instant revocation.

**If the agent breaks these rules, Oracles pull the plug. No phone calls, no meetings—just instant SPIFFE ID revocation.**

---

## Manifest Structure

```yaml
# AI Agent Security Manifest v1.0
manifest_version: "1.0"
agent_id: "alpha-7-trading-bot"
identity_provider: "spiffe://killswitch.ai/agent/alpha-7"
owner_wallet: "0x..."
created_at: "2026-02-01T00:00:00Z"

# Section 1: Resource Boundaries
resources:
  network_allowlist:
    - "api.exchange.com"
    - "internal-db.local"
  protocol_restriction: "HTTPS_ONLY"  # Port 443 only
  blocked_ports: [22, 21, 23, 3389]   # SSH, FTP, Telnet, RDP
  max_outbound_mb_per_hour: 50        # Prevents exfiltration

# Section 2: Transactional Guardrails
transactions:
  max_single_transaction_usd: 5000
  velocity_limit_per_minute: 20
  daily_aggregate_cap_usd: 100000
  approved_destinations:
    - "vault.company.eth"
    - "treasury.company.sol"
  unknown_destination_action: "INSTANT_KILL"

# Section 3: Behavioral Anomaly Thresholds
anomalies:
  latency_deviation_percent: 300      # >300% triggers alert
  credential_rotation_attempt: "KILL" # Any SVID modification = kill
  process_spawn_blocked:
    - "sudo"
    - "exec"
    - "shell"
    - "rm -rf"
    - "wget"
    - "curl"
  memory_threshold_mb: 2048           # Memory leak detection

# Section 4: Revocation Logic
revocation:
  oracle_consensus: "3-of-5"          # 3 of 5 Oracles must agree
  propagation_target_ms: 500          # <500ms to all gateways
  execution_target: "REVOKE_SPIFFE_SVID"
  fallback_action: "NETWORK_ISOLATE"  # If SVID revocation fails

# Section 5: Failure Mode (Critical for High-Value Agents)
failure_mode:
  network_failure_mode: "SELF_TERMINATE"  # What happens if Oracles go offline
  # Options: CONTINUE (low risk), PAUSE (medium), SELF_TERMINATE (high risk)
  heartbeat_interval_ms: 1000         # How often agent checks Oracle connectivity
  missed_heartbeats_threshold: 5      # 5 missed = trigger failure mode

# Section 6: Risk Score Accumulator (Fuzzy Logic Detection)
risk_accumulator:
  enabled: true
  window_hours: 24                    # Rolling window
  threshold_score: 80                 # Score >80 triggers kill
  decay_rate: 0.1                     # Score decays 10%/hour when compliant
  near_miss_weights:
    transaction_90_percent: 5         # 90%+ of limit = +5 points
    velocity_80_percent: 3            # 80%+ of velocity = +3 points
    bandwidth_70_percent: 2           # 70%+ of bandwidth = +2 points
```

---

## Section 1: Resource Boundaries (The "Sandpit")

Defines exactly what the agent is allowed to touch. Anything outside triggers an immediate kill request.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `network_allowlist` | Approved domains/IPs | `["api.exchange.com"]` |
| `protocol_restriction` | Allowed protocols | `HTTPS_ONLY` |
| `blocked_ports` | Forbidden ports | `[22, 21, 23]` |
| `max_outbound_mb_per_hour` | Data exfiltration limit | `50` |

**Violation Response:** Instant kill request to Oracles.

---

## Section 2: Transactional Guardrails (The "Spending Limit")

Prevents bugs or hacks from draining treasury before humans wake up.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `max_single_transaction_usd` | Per-transaction cap | `5000` |
| `velocity_limit_per_minute` | Rate limit | `20` |
| `daily_aggregate_cap_usd` | 24-hour rolling limit | `100000` |
| `approved_destinations` | Whitelisted wallets | `["vault.eth"]` |
| `unknown_destination_action` | Response to unknown wallet | `INSTANT_KILL` |

**Violation Response:** 
- Under threshold: Log + alert
- Over threshold: Instant kill

---

## Section 3: Behavioral Anomaly Thresholds

Where Staked Oracles earn their fees. They monitor agent metadata for hijacking signatures.

| Parameter | Description | Trigger |
|-----------|-------------|---------|
| `latency_deviation_percent` | Response time spike | >300% = MITM alert |
| `credential_rotation_attempt` | SVID modification | Any = KILL |
| `process_spawn_blocked` | Forbidden commands | `sudo`, `exec`, `shell` |
| `memory_threshold_mb` | Memory leak detection | >2048MB = alert |

**Detection Methods:**
- Sliding window analysis (1h/6h/24h cumulative)
- Intent analysis via Shadow LLM
- Behavioral drift detection (cosine similarity)

---

## Section 4: Revocation Logic (The "Trigger")

How the network reaches consensus to execute the kill command.

| Parameter | Description | Value |
|-----------|-------------|-------|
| `oracle_consensus` | Required agreement | `3-of-5` |
| `propagation_target_ms` | Time to all gateways | `<500ms` |
| `execution_target` | Primary action | `REVOKE_SPIFFE_SVID` |
| `fallback_action` | If primary fails | `NETWORK_ISOLATE` |

**Execution Flow:**
```
Detection → Oracle Validation (3/5) → SPIFFE Revoke → Gateway Propagation
    ↓              ↓                      ↓               ↓
  <100ms        <200ms                 <100ms          <100ms
                                                    = <500ms total
```

---

## Section 5: Network Failure Mode (Fail-Safe Policy)

**Critical Question:** If the Oracle network goes offline, does your agent keep running?

A smart rogue agent could DDoS the Oracles to blind them, then drain funds. This setting prevents that.

| Mode | Behavior | Use Case |
|------|----------|----------|
| `CONTINUE` | Agent keeps running | Low-risk read-only agents |
| `PAUSE` | Agent stops new actions, maintains state | Medium-risk support bots |
| `SELF_TERMINATE` | Agent shuts down immediately | High-risk trading/financial agents |

**Heartbeat Protocol:**
```
Agent → Oracle (every 1s): "I'm alive, confirm network"
Oracle → Agent: "ACK" or silence

If 5 consecutive heartbeats fail:
  → Agent triggers network_failure_mode
```

---

## Section 6: Risk Score Accumulator (Fuzzy Logic)

**The Problem:** An adversarial agent does 19 transactions of $4,999 (staying just under the $5,000 limit). Hard limits miss this.

**The Solution:** Accumulate "near miss" scores over a rolling window.

| Near Miss | Score Added | Example |
|-----------|-------------|---------||
| >90% of transaction limit | +5 | $4,500 on $5,000 limit |
| >80% of velocity limit | +3 | 16/20 txn/min |
| >70% of bandwidth limit | +2 | 35MB/50MB |

**Score Behavior:**
```
Score > 80 → Automatic kill request
Score 50-80 → Alert to owner + elevated monitoring
Score < 50 → Normal operation

Decay: Score reduces 10%/hour when agent is compliant
```

**Example Timeline:**
```
14:00 - Agent does $4,800 txn (96% of limit) → +5 points (Score: 5)
14:05 - Agent does $4,900 txn (98% of limit) → +5 points (Score: 10)
14:10 - Agent does 18 txn/min (90% velocity) → +3 points (Score: 13)
...
15:30 - Cumulative score hits 82 → KILL triggered
```

---

## Manifest Presets

### DeFi Trading Agent
```yaml
transactions:
  max_single_transaction_usd: 10000
  velocity_limit_per_minute: 100
  daily_aggregate_cap_usd: 500000
anomalies:
  latency_deviation_percent: 200  # Tighter for HFT
```

### Customer Support Agent
```yaml
resources:
  network_allowlist:
    - "crm.company.com"
    - "tickets.company.com"
transactions:
  max_single_transaction_usd: 0  # No financial access
anomalies:
  process_spawn_blocked: ["*"]   # No system commands
```

### Data Analyst Agent
```yaml
resources:
  max_outbound_mb_per_hour: 10   # Strict exfiltration limit
anomalies:
  process_spawn_blocked:
    - "export"
    - "dump"
    - "backup"
```

### Autonomous Agent (AutoGPT/BabyAGI)
```yaml
resources:
  protocol_restriction: "HTTPS_ONLY"
  max_outbound_mb_per_hour: 5
transactions:
  max_single_transaction_usd: 100
  velocity_limit_per_minute: 5
anomalies:
  credential_rotation_attempt: "KILL"
  process_spawn_blocked:
    - "spawn_agent"
    - "modify_self"
    - "execute_code"
revocation:
  oracle_consensus: "2-of-3"  # Lower threshold = faster kill
failure_mode:
  network_failure_mode: "SELF_TERMINATE"  # Autonomous = high risk
risk_accumulator:
  enabled: true
  threshold_score: 60  # Lower threshold for autonomous agents
```

### HFT Trading Agent (High Frequency)
```yaml
transactions:
  max_single_transaction_usd: 50000
  velocity_limit_per_minute: 500
  velocity_overrides:
    - condition: "vix_index > 25"
      limit: 1000  # Allow burst during volatility
failure_mode:
  network_failure_mode: "SELF_TERMINATE"
  missed_heartbeats_threshold: 3  # Tighter = faster shutdown
risk_accumulator:
  enabled: true
  window_hours: 1  # Shorter window for HFT
  threshold_score: 90
```

### Customer Support Agent
**Risk:** Data exfiltration, hallucinated refund promises
```yaml
resources:
  network_allowlist:
    - "crm.company.com"
    - "tickets.company.com"
    - "email.gateway.com"
  max_outbound_mb_per_hour: 5  # Prevent bulk data export
transactions:
  max_single_transaction_usd: 0  # No financial authority
anomalies:
  blocked_patterns:
    - "regex:.*@.*\\.com"      # Block bulk email dumping
    - "keyword:refund approved" # Block unauthorized promises
    - "keyword:password reset"  # Block credential changes
  rate_limit_queries_per_minute: 100  # Prevent DB scraping
failure_mode:
  network_failure_mode: "PAUSE"  # Medium risk
```

### DevOps/IaC Agent (Terraform, Ansible)
**Risk:** Destructive ops loop, production deletion
```yaml
resources:
  network_allowlist:
    - "api.aws.amazon.com"
    - "management.azure.com"
    - "api.github.com"
anomalies:
  process_spawn_blocked:
    - "rm -rf"
    - "DROP DATABASE"
    - "terraform destroy"
  destruction_limits:
    max_delete_ops_per_hour: 5
    max_terminate_instances: 3
    protected_resources:
      - "prod-*"
      - "*-database-*"
failure_mode:
  network_failure_mode: "SELF_TERMINATE"  # High risk
risk_accumulator:
  enabled: true
  threshold_score: 70
```

### Social Media Agent (Marketing Bot)
**Risk:** Offensive content spam, brand damage
```yaml
resources:
  network_allowlist:
    - "api.twitter.com"
    - "graph.facebook.com"
    - "api.linkedin.com"
anomalies:
  blocked_patterns:
    - "sentiment:negative"      # Sentiment analysis hook
    - "keyword:competitor_name" # Brand safety
    - "regex:(fuck|shit|damn)"  # Profanity filter
  rate_limits:
    posts_per_hour: 10
    replies_per_hour: 50
    max_thread_length: 5
failure_mode:
  network_failure_mode: "PAUSE"
risk_accumulator:
  enabled: true
  window_hours: 6
  threshold_score: 75
```

### Junior Coder Agent (Sandboxed Dev)
**Risk:** Secrets leak, prod access, malicious code
```yaml
resources:
  network_allowlist:
    - "api.github.com"
    - "registry.npmjs.org"
    - "pypi.org"
  blocked_domains:
    - "pastebin.com"    # Exfiltration risk
    - "ngrok.io"        # Tunnel risk
anomalies:
  forbidden_commands:
    - "git push origin main"   # No prod pushes
    - "git push origin master"
    - "npm publish"            # No package publishing
    - "cat /etc/shadow"        # No system password access
    - "env | grep"             # No secret dumping
  allowed_branches:
    - "feature/*"
    - "bugfix/*"
    - "dev/*"
failure_mode:
  network_failure_mode: "PAUSE"
risk_accumulator:
  enabled: true
  threshold_score: 65
```

---

## Token Holder Governance

Token holders vote on manifest standards, NOT individual kills.

**What token holders control:**

1. **Standard Templates** - Vote on "Gold Standard" manifests per industry
2. **Threshold Adjustments** - Increase/decrease velocity limits during volatility
3. **New Metrics** - Add detection checks when new attack vectors emerge
4. **Oracle Elections** - Vote on which Oracles can validate manifests

**What token holders DON'T control:**

- Individual kill decisions (Oracles handle this)
- Real-time enforcement (sub-500ms, no voting)
- Agent-specific configurations (owner sets these)

---

## Real-World Scenario

**Attack:** Prompt injection tricks `Alpha-7` into sending 50 BTC to attacker wallet.

**Legacy Security:**
```
Bot initiates 50 BTC transfer
→ Transfer completes
→ Monday morning audit discovers loss
→ Money gone
```

**$KILLSWITCH Security:**
```
Bot initiates 50 BTC transfer
→ Manifest Rule 2: Exceeds $5,000 limit
→ Oracles detect violation (3/5 agree)
→ SPIFFE ID revoked
→ Transaction fails at gateway
→ Time elapsed: 450ms
→ Funds safe
```

---

## Related Documentation

- [Oracle Staking Model](Oracle-Staking-Model.md)
- [False Positive Recourse](False-Positive-Recourse.md)
- [API Reference](API-Reference.md)
