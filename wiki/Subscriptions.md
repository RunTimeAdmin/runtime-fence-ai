# Subscriptions

Runtime Fence offers tiered subscriptions to match your needs.

## Subscription Tiers

| Tier | Price | Agents | API Calls | Features |
|------|-------|--------|-----------|----------|
| **Basic** | $5/mo | 1 | - | Dashboard, local usage |
| **Pro** | $50/mo | 3 | 100/mo | Analytics, cloud monitoring, API access |
| **Team** | $250/mo | 10 | 1,000/mo | Orchestration, SMS alerts, webhooks |
| **Enterprise** | $1,000/mo | Unlimited | 10,000/mo | Threat detection, custom integrations, SLA |
| **VIP** | $5,000/mo | Unlimited | Unlimited | Early access, custom dev, quarterly calls |

## Payment Methods

### Credit Card (Stripe)

Standard USD payments via credit/debit card.

## Tier Features

### Basic ($5/mo)
- 1 agent
- Web dashboard
- Local usage only
- Community support

### Pro ($50/mo)
- 3 agents
- 100 API calls/month
- Advanced analytics
- Cloud monitoring
- API access

### Team ($250/mo)
- 10 agents
- 1,000 API calls/month
- Multi-agent orchestration
- SMS alerts
- Webhooks

### Enterprise ($1,000/mo)
- Unlimited agents
- 10,000 API calls/month
- Threat detection
- Custom integrations
- SLA guarantee

### VIP ($5,000/mo)
- Everything in Enterprise
- Unlimited API calls
- Early access to features
- Custom development
- Quarterly strategy calls

## Usage Limits

Each tier has monthly limits that reset on the 1st:

```typescript
// Check current usage
const usage = getUsageInfo(userId, tier);

console.log(usage.apiCallsUsed);      // 45
console.log(usage.apiCallsLimit);     // 100
console.log(usage.percentUsed);       // 45%
```

When you hit your limit:
- API calls return 429 (Rate Limit Exceeded)
- Upgrade prompt displayed
- Usage resets on the 1st

## Managing Subscriptions

### Upgrade/Downgrade

```typescript
await subscriptionService.changeTier(subscriptionId, "team");
```

Prorated charges apply.

### Cancel

```typescript
await subscriptionService.cancelSubscription(subscriptionId);
```

Subscription remains active until period end.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/subscription` | GET | Get current subscription |
| `/api/subscription` | POST | Create subscription |
| `/api/subscription/cancel` | POST | Cancel subscription |
| `/api/subscription/usage` | GET | Get usage stats |
