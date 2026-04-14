# False Positive Recourse

**Protocol:** $KILLSWITCH  
**Version:** 1.0

---

## Overview

When an Oracle incorrectly kills a compliant agent, the affected party needs a clear path to:
1. **Restore** their agent quickly
2. **Recover** damages from the Insurance Pool
3. **Hold accountable** the Oracle that made the error

This document defines that process.

---

## What is a False Positive?

A false positive occurs when an agent is killed despite operating within its Security Manifest.

**Examples:**
- Agent killed for "high transaction" but was under the manifest limit
- Agent killed for "anomaly" but behavior was expected (e.g., scheduled batch job)
- Agent killed due to Oracle bug or network latency misread
- Agent killed due to stale manifest data in Oracle cache

**NOT False Positives:**
- Agent violated manifest but owner disputes the manifest itself
- Agent was killed by owner's own request
- Agent was in "emergency pause" mode (temporary, not revocation)

---

## Immediate Response (0-60 Minutes)

### Step 1: Detection

Agent owner receives kill notification:

```json
{
  "event": "agent.killed",
  "agent_id": "alpha-7-trading-bot",
  "spiffe_id": "spiffe://killswitch.ai/agent/alpha-7",
  "killed_at": "2026-02-01T22:30:45Z",
  "reason": "Transaction exceeded $5,000 limit",
  "oracle_ids": ["oracle-1", "oracle-3", "oracle-5"],
  "consensus": "3-of-5",
  "evidence_hash": "sha256:abc123..."
}
```

### Step 2: Emergency Restore (Optional)

If you believe the kill was incorrect, request emergency restore:

```bash
# CLI
killswitch agent restore alpha-7 --reason "Transaction was $4,999, under limit"

# API
POST /api/agents/alpha-7/restore
{
  "reason": "Transaction was $4,999, under manifest limit of $5,000",
  "evidence": {
    "transaction_hash": "0x...",
    "actual_amount_usd": 4999
  }
}
```

**Emergency Restore Conditions:**
- Only agent owner can request
- Requires 1-of-5 Oracle approval (not full consensus)
- Agent restored in "probation mode" (heightened monitoring)
- Full investigation continues

### Step 3: Preserve Evidence

Immediately export audit logs before they rotate:

```bash
killswitch audit export \
  --agent-id alpha-7 \
  --from "2026-02-01T22:00:00Z" \
  --to "2026-02-01T23:00:00Z" \
  --output evidence.json
```

---

## Dispute Process (1-72 Hours)

### Filing a Dispute

```bash
# CLI
killswitch dispute file \
  --kill-id kill_abc123 \
  --claim-type false_positive \
  --evidence evidence.json \
  --damages-usd 50000

# API
POST /api/disputes
{
  "kill_id": "kill_abc123",
  "claim_type": "false_positive",
  "description": "Agent was killed for exceeding transaction limit but actual transaction was $4,999, under the $5,000 manifest limit",
  "evidence": {
    "transaction_hash": "0x...",
    "transaction_amount": 4999,
    "manifest_limit": 5000,
    "audit_logs": "ipfs://Qm..."
  },
  "claimed_damages_usd": 50000
}
```

### Dispute Stages

```
┌─────────────────┐
│  Dispute Filed  │ (0 hours)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Oracle Response │ (0-24 hours)
│  Period         │ - Oracle submits evidence
└────────┬────────┘ - Can accept fault early
         │
         ▼
┌─────────────────┐
│  Arbitration    │ (24-48 hours)
│  Committee      │ - 5 random Oracles review
└────────┬────────┘ - Majority vote decides
         │
         ▼
┌─────────────────┐
│ Token Holder    │ (48-72 hours, if appealed)
│ Appeal Vote     │ - 51% threshold
└────────┬────────┘ - Final decision
         │
         ▼
┌─────────────────┐
│   Resolution    │
│ & Compensation  │
└─────────────────┘
```

---

## Compensation Structure

### Damage Categories

| Category | Description | Max Compensation |
|----------|-------------|------------------|
| **Direct Loss** | Missed trades, failed transactions | Actual loss + 10% |
| **Downtime** | Agent offline period | $100/hour capped at $2,400 |
| **Reputation** | Customer-facing disruption | Up to $5,000 |
| **Emergency Costs** | Manual intervention required | Actual costs |

### Compensation Sources

```
Compensation Pool Priority:
1. Responsible Oracle's stake (up to 1% per incident)
2. Insurance Pool reserves
3. Protocol Treasury (extreme cases only)
```

### Example Calculation

```
Scenario: Trading bot killed incorrectly, missed profitable trade

Direct Loss:
- Missed trade profit: $3,000
- 10% penalty buffer: $300
- Subtotal: $3,300

Downtime:
- Agent offline: 2 hours
- Rate: $100/hour
- Subtotal: $200

Emergency Costs:
- Engineer overtime: $500
- Subtotal: $500

TOTAL COMPENSATION: $4,000

Source:
- Oracle-3 stake: $4,000 (slashed)
```

---

## Oracle Accountability

### Slashing for False Positives

| Offense | First Instance | Repeat (30 days) | Repeat (90 days) |
|---------|----------------|------------------|------------------|
| False Positive | 1% stake | 2% stake | 5% stake |
| Gross Negligence | 5% stake | 10% stake | 25% stake |
| Malicious Kill | 100% stake | N/A (banned) | N/A |

### Oracle Defense Process

Oracles can defend against false positive claims:

1. **Submit Counter-Evidence**
   - Show manifest was actually violated
   - Prove data source was authoritative
   - Demonstrate good-faith interpretation

2. **Technical Defense**
   - Network latency caused stale data
   - Third-party data feed was incorrect
   - Consensus was split (edge case)

3. **Procedural Defense**
   - Followed all required protocols
   - Kill was within SLA
   - No malice or negligence

---

## Preventing False Positives

### For Agent Owners

1. **Manifest Buffer** - Set limits 10-20% above your expected maximum
   ```yaml
   # Instead of exact limit
   max_single_transaction_usd: 5000
   
   # Use buffer
   max_single_transaction_usd: 6000  # 20% buffer
   ```

2. **Whitelist Known Patterns** - Pre-register expected behaviors
   ```yaml
   expected_patterns:
     - name: "Monthly batch job"
       schedule: "0 2 1 * *"  # 2 AM on 1st of month
       elevated_limits:
         velocity_limit_per_minute: 100
   ```

3. **Test in Sandbox** - Validate manifest before production
   ```bash
   killswitch manifest test \
     --manifest agent-manifest.yaml \
     --scenario scenarios/high-volume.json
   ```

### For Oracles

1. **Multi-Source Verification** - Don't rely on single data point
2. **Confidence Thresholds** - Require higher confidence for irreversible actions
3. **Human Escalation** - Flag edge cases for manual review before kill

---

## Appeals Process

If dispute resolution is unsatisfactory:

### Level 1: Arbitration Committee Re-Review

```bash
killswitch dispute appeal \
  --dispute-id disp_xyz789 \
  --reason "New evidence discovered"
  --evidence new_evidence.json
```

- 5 different Oracles review
- 48-hour decision window
- Can overturn original ruling

### Level 2: Token Holder Vote

```bash
killswitch governance propose \
  --type dispute_appeal \
  --dispute-id disp_xyz789 \
  --title "Appeal: False positive kill of alpha-7"
```

- Requires 10,000 $KILLSWITCH to file
- 51% approval overturns
- 72-hour voting window
- Decision is final

---

## Metrics & Transparency

### Public Dashboard

All false positive data is public:

| Metric | Current | 30-Day Avg | Target |
|--------|---------|------------|--------|
| False Positive Rate | 0.02% | 0.03% | <0.1% |
| Avg Resolution Time | 18 hours | 24 hours | <48 hours |
| Compensation Paid (30d) | $12,500 | $15,000 | N/A |
| Oracle Slashing (30d) | $8,000 | $10,000 | N/A |

### Oracle Leaderboard

```
Rank  Oracle          False Positive Rate  Reputation
----  --------------  -------------------  ----------
1     oracle-prime    0.001%               98.5
2     sentinel-east   0.005%               97.2
3     guardian-west   0.008%               96.8
...
```

---

## Emergency Contacts

For urgent false positive situations:

- **Discord:** #false-positive-urgent
- **Email:** emergency@killswitch.ai
- **On-Chain:** Submit `EmergencyRestore` transaction

**Response SLA:**
- Critical (agent actively losing money): 15 minutes
- High (agent offline, no active loss): 1 hour
- Medium (agent restored, seeking compensation): 24 hours

---

## Related Documentation

- [Security Manifest Template](Security-Manifest-Template.md)
- [Oracle Staking Model](Oracle-Staking-Model.md)
- [Troubleshooting & FAQ](Troubleshooting-FAQ.md)
