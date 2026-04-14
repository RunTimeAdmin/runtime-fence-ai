# Runtime Fence - Enterprise Edition Pricing Strategy

**Document Status:** Business Strategy
**Last Updated:** February 2, 2026

---

## Executive Summary

Runtime Fence offers a dual-tier solution:
- **Standard Edition** for SMBs/startups (API key-based)
- **Enterprise Edition** for large-scale deployments (SPIFFE/SPIRE integration)

---

## Product Tiers

### 1. Standard Edition (API Key-Based)

**Target Market:**
- Startups and SMBs
- Development teams
- Small AI agent deployments (1-50 agents)
- Budget-conscious organizations

**Features:**
- API key-based authentication
- Runtime Fence core engine
- Basic monitoring dashboard
- Risk scoring (0-100)
- Emergency kill switch
- Python & TypeScript SDKs
- Community support

**Pricing:**

| Tier | Price | Agents | Actions/Day |
|------|-------|--------|-------------|
| Basic | $49/mo | 5 | 10K |
| Pro | $149/mo | 20 | 100K |
| Team | $349/mo | 50 | 1M |

**Deployment Time:** <1 hour

---

### 2. Enterprise Edition (SPIFFE/SPIRE Integration)

**Target Market:**
- Large enterprises (100+ agents)
- Financial institutions
- Healthcare systems
- Government agencies
- Regulated industries

**Features Beyond Standard:**

| Category | Capabilities |
|----------|--------------|
| **Zero-Trust Identity** | SPIFFE/SPIRE, mTLS, auto-rotating SVIDs, <30s kill |
| **Compliance** | Immutable audit logs, SOC2/ISO 27001, regulatory support |
| **Architecture** | Multi-cluster, centralized identity, HA, DR |
| **Security** | Circuit breakers, anomaly detection, NetworkPolicy isolation |
| **Support** | Dedicated account manager, 24/7 SLA, on-site assistance |

---

## Enterprise Pricing Tiers

### Silver - $100,000/year

**Target:** Organizations getting started with SPIFFE

| Included | Limit |
|----------|-------|
| AI Agents | 100 |
| K8s Clusters | 2 |
| Support | 8x5 |
| Reviews | Quarterly |
| Deployment | Remote |

**Overage:**
- +$500/agent over 100
- +$2,000/cluster
- +$2,500/integration

**Implementation:** $25,000 (1-2 weeks)

---

### Gold - $300,000/year

**Target:** Enterprises with regulatory requirements

| Included | Limit |
|----------|-------|
| AI Agents | 500 |
| K8s Clusters | 5 |
| Compliance | SOC2, ISO 27001 |
| Support | 24/7, 1hr response |
| Reviews | Monthly |
| On-site | 3 days |

**Overage:**
- +$400/agent over 500
- +$1,500/cluster
- +$2,000/integration

**Implementation:** $75,000 (3-4 weeks)

---

### Platinum - $750,000/year

**Target:** Fortune 500, financial institutions, government

| Included | Limit |
|----------|-------|
| AI Agents | Unlimited |
| K8s Clusters | Unlimited |
| Compliance | SOC2, ISO, PCI-DSS, HIPAA |
| Support | 24/7, 15min response, dedicated engineer |
| Reviews | Weekly |
| On-site | 10 days |
| Source Code | Escrow access |
| Custom Dev | Included |

**Overage:** None (all inclusive)
- +$1,500/day additional on-site

**Implementation:** $150,000 (6-8 weeks)

---

## ROI Analysis

### Cost of AI Security Breach

| Category | Range |
|----------|-------|
| Financial impact | $2.5M - $10M |
| Regulatory fines | $500K - $2M |
| Reputation damage | $1M - $5M |
| Operational disruption | $500K - $1M |
| **Total** | **$4.5M - $18M** |

### Enterprise Platinum ROI (3 Years)

**Investment:**
- License: $750K × 3 = $2,250,000
- Implementation: $150,000
- **Total: $2,400,000**

**ROI if prevents ONE breach:**

| Scenario | Breach Cost | ROI |
|----------|-------------|-----|
| Conservative | $4.5M | 187% |
| Average | $10M | 316% |
| High | $18M | 650% |

---

## Revenue Projections (Year 1)

| Scenario | Silver | Gold | Platinum | Impl Fees | **Total** |
|----------|--------|------|----------|-----------|-----------|
| Conservative | 5×$100K | 3×$300K | 1×$750K | $200K | **$2.35M** |
| Moderate | 10×$100K | 5×$300K | 2×$750K | $400K | **$4.4M** |
| Optimistic | 20×$100K | 10×$300K | 5×$750K | $750K | **$9.5M** |

---

## Go-to-Market Timeline

| Phase | Timeline | Milestones |
|-------|----------|------------|
| **Foundation** | Weeks 1-8 | SPIFFE integration, sales materials, compliance prep |
| **Beta Launch** | Weeks 9-12 | 3-5 design partners, feedback loop, case studies |
| **Public Launch** | Weeks 13-16 | PR campaign, launch event, CISO marketing |
| **Expansion** | Weeks 17-24 | Industry campaigns, partner channels, sales hiring |

---

## Key Success Metrics

| Quarter | Targets |
|---------|---------|
| Q1 | SPIFFE complete, 2 design partners, beta launch |
| Q2 | 3 paying clients, $500K ARR, 1 case study |
| Q3 | 10 paying clients, $1.5M ARR, compliance certified |
| Q4 | 20 paying clients, $3M ARR, sales team of 3 |

---

## Competitive Positioning

### vs. Open Source (NetworkPolicies, etc.)

| Feature | Open Source | Runtime Fence |
|---------|-------------|-------------|
| Purpose-built for AI | ❌ | ✅ |
| Behavioral analysis | ❌ | ✅ |
| Kill switch speed | Manual | <30 seconds |
| SDKs & tools | ❌ | ✅ |
| Enterprise support | ❌ | ✅ |
| Compliance-ready | ❌ | ✅ |

### vs. Enterprise AI Security Vendors

| Feature | Competitors | Runtime Fence |
|---------|-------------|-------------|
| Zero-trust | Perimeter-based | SPIFFE/SPIRE |
| Agent-specific identity | ❌ | ✅ |
| Immutable audit | ❌ | ✅ |
| TCO | Higher | Lower |
| Pricing transparency | Hidden costs | Transparent |
| Open source core | ❌ | ✅ |

---

## Ideal Customer Profile

**Industry:** Financial Services, Healthcare, Government, Technology

**Company Profile:**
- Employees: 1,000+
- Revenue: $100M+
- AI Agents: 100+ (current or planned)

**Decision Makers:**
- CISO
- CTO/VP Engineering
- VP Infrastructure
- Head of AI/ML

**Pain Points:**
- AI agent security concerns
- Compliance requirements
- Runaway agent fear
- Audit trail needs
- API key management overhead

---

## Implementation Checklist

### Pre-Deployment
- [ ] Discovery call and requirements
- [ ] Technical assessment
- [ ] Agent inventory
- [ ] Compliance requirements documented
- [ ] Contract signed

### Deployment
- [ ] SPIRE server deployed
- [ ] K8s clusters configured
- [ ] Agent identity framework
- [ ] mTLS certificates
- [ ] Network policies
- [ ] Monitoring/alerting
- [ ] Audit logging
- [ ] Kill switch testing

### Post-Deployment
- [ ] Team training
- [ ] Documentation delivered
- [ ] Go-live verification
- [ ] 30-day review scheduled
- [ ] Ongoing support established

---

## Next Steps

1. ✅ Complete SPIFFE/SPIRE integration (DONE)
2. [ ] Develop enterprise sales collateral
3. [ ] Identify design partners
4. [ ] Begin compliance certification
5. [ ] Hire enterprise sales engineer
6. [ ] Launch Enterprise beta program

---

**Runtime Fence - Because every AI needs an off switch.**
