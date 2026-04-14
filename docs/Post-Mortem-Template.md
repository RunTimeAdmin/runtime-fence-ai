# Post-Mortem & Compensation Claim

**Protocol:** $KILLSWITCH  
**Template Version:** 1.1

---

## Instructions

Use this template when filing a wrongful revocation claim. Be precise. Data-driven claims get paid; emotional appeals get ignored.

**Submit via:**
- CLI: `killswitch dispute file --report claim.md`
- API: `POST /api/disputes`
- Dashboard: Disputes > New Claim

---

# Post-Mortem & Compensation Claim

**Incident ID:** `KS-YYYY-MMDD-###`  
**Status:** Dispute Filed  
**Claimant:** [Your Entity Name / Wallet Address]

---

## 1. Executive Summary

| Field | Value |
|-------|-------|
| **Incident Window** | [Start Time] to [End Time] (UTC) |
| **Total Downtime** | [Minutes/Seconds] |
| **Impacted Agent** | `[Agent Name]` |
| **SPIFFE ID** | `spiffe://killswitch.ai/agent/[id]` |
| **Summary** | At [Time], the $KILLSWITCH network revoked the identity of a healthy agent performing legitimate [Transaction Type]. This was a False Positive triggered by [Rule Name]. |

---

## 2. The "False Positive" Proof

| Field | Value |
|-------|-------|
| **Triggering Manifest Rule** | Rule [X.X] ([Rule Name]) |
| **Threshold** | [Configured Limit] |
| **Actual Behavior** | [What the agent actually did] |
| **Justification** | [Why this was legitimate] |
| **Evidence** | [IPFS CID / Transaction Hash / Signed Log] |

**Example:**
```
Triggering Rule: Rule 2.2 (Velocity Limit: >20 txn/min)
Actual Behavior: Agent executed 25 transactions within 60 seconds.
Justification: Pre-scheduled rebalancing event tied to quarterly options expiry.
Evidence: ipfs://Qm... (Signed execution log showing owner authorization)
```

---

## 3. Detailed Timeline (The "Kill Chain")

| Timestamp (UTC) | Event | Data Source |
|-----------------|-------|-------------|
| **14:00:01** | Agent begins [operation]. | Agent Logs |
| **14:00:15** | Oracle Node `0xABC...` issues Kill Request. | $KILLSWITCH Chain |
| **14:00:16** | Consensus reached (3/5 Oracles). SVID Revoked. | $KILLSWITCH Chain |
| **14:00:17** | Agent loses database/exchange connectivity. | Gateway Logs |
| **14:05:00** | Owner initiates Emergency Bypass. | Governance Portal |
| **14:05:30** | Agent restored in Safe Mode. | $KILLSWITCH Chain |

---

## 4. Financial Impact & Compensation Request

| Category | Amount (USD) | Evidence |
|----------|--------------|----------|
| **Direct Losses** | $[X,XXX] | [Missed trades, liquidated positions] |
| **Operational Costs** | $[XXX] | [Emergency response, manual intervention] |
| **Service Credits** | $[XXX] | [Protocol fees during downtime] |
| **Total Claim** | **$[X,XXX]** | |

**Payment Request:**
- Amount: [X,XXX] $KILLSWITCH tokens (or USDC equivalent)
- Wallet: `0x...`
- Chain: [Ethereum / Solana]

---

## 5. Oracle Accountability

| Oracle ID | Vote | Action Requested |
|-----------|------|------------------|
| `oracle-1` | KILL | Slash 1% stake |
| `oracle-2` | NO_KILL | None |
| `oracle-3` | KILL | Slash 1% stake |
| `oracle-4` | NO_KILL | None |
| `oracle-5` | KILL | Warning |

**Rationale:** Oracles 1, 3, and 5 failed to verify transaction context before voting KILL. Transaction destinations were pre-approved "Safe" addresses in the manifest.

---

## 6. Proposed Manifest Tuning

To prevent recurrence:

| Parameter | Current Value | Proposed Value | Rationale |
|-----------|---------------|----------------|-----------|
| `velocity_limit_per_minute` | 20 | 50 | Insufficient for rebalancing events |
| `velocity_override_condition` | None | `market_volatility > 20` | Allow burst during high-vol periods |

**Updated Manifest Section:**
```yaml
transactions:
  velocity_limit_per_minute: 20
  velocity_overrides:
    - condition: "vix_index > 20"
      limit: 50
    - condition: "scheduled_rebalance == true"
      limit: 100
```

---

## 7. Evidence Package

| Type | Hash/CID | Description |
|------|----------|-------------|
| Audit Logs | `ipfs://Qm...` | Agent activity 14:00-15:00 UTC |
| Kill Signal | `0x...` | On-chain kill transaction |
| Oracle Logs | `ipfs://Qm...` | Oracle-1 decision data |
| Price Feed | `0x...` | Chainlink round ID at kill time |
| Owner Auth | `ipfs://Qm...` | Signed rebalance authorization |

---

## 8. Attestation

I attest that the information in this claim is accurate. False claims result in stake forfeiture.

| Field | Value |
|-------|-------|
| **Wallet** | `0x...` |
| **Signature** | `0x...` |
| **Timestamp** | [ISO 8601 UTC] |

---

## Processing SLA

| Stage | Target | Status |
|-------|--------|--------|
| Acknowledgment | 1 hour | Pending |
| Oracle Response | 24 hours | Pending |
| Arbitration | 48 hours | Pending |
| Payment | 24 hours | Pending |
| **Total** | **5 days** | |

---

## CLI Submission

```bash
# Submit claim
killswitch dispute file \
  --incident-id KS-2026-0201-001 \
  --agent-id alpha-7 \
  --claim-usd 4000 \
  --evidence-dir ./evidence/ \
  --sign

# Check status
killswitch dispute status KS-2026-0201-001

# Appeal if denied
killswitch dispute appeal KS-2026-0201-001 --reason "New evidence"
```

---

## Common Rejection Reasons (Avoid These)

| Mistake | Fix |
|---------|-----|
| Missing timestamps | Use UTC ISO 8601 for all times |
| No evidence hashes | Upload to IPFS; include CIDs |
| Vague "it was legitimate" | Prove it: signed logs, tx hashes |
| Claiming without manifest context | Show the exact rule that was too tight |
| Late submission | File within 72 hours of incident |

---

## Related Documentation

- [False Positive Recourse](False-Positive-Recourse.md)
- [Oracle Staking Model](Oracle-Staking-Model.md)
- [Security Manifest Template](Security-Manifest-Template.md)
