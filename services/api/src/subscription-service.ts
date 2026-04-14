/**
 * $KILLSWITCH Subscription Service - Stripe integration
 */
import Stripe from 'stripe';

export const TIERS = {
  basic: { price: 5, agents: 1, apiCalls: 0, storageGb: 0 },
  pro: { price: 50, agents: 3, apiCalls: 100, storageGb: 1 },
  team: { price: 250, agents: 10, apiCalls: 1000, storageGb: 10 },
  enterprise: { price: 1000, agents: -1, apiCalls: 10000, storageGb: 100 },
  vip: { price: 5000, agents: -1, apiCalls: -1, storageGb: -1 },
} as const;

export type TierName = keyof typeof TIERS;

export class SubscriptionService {
  private stripe: Stripe;

  constructor() {
    this.stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
      apiVersion: '2025-01-27.acacia' as Stripe.LatestApiVersion,
    });
  }

  async createSubscription(userId: string, email: string, tier: TierName, discountPercent = 0) {
    const customer = await this.getOrCreateCustomer(userId, email);
    const priceId = process.env[`STRIPE_PRICE_${tier.toUpperCase()}`] || '';

    let couponId: string | undefined;
    if (discountPercent > 0) {
      const coupon = await this.stripe.coupons.create({
        percent_off: discountPercent,
        duration: 'forever',
        name: `Discount ${discountPercent}%`,
      });
      couponId = coupon.id;
    }

    const subscription = await this.stripe.subscriptions.create({
      customer: customer.id,
      items: [{ price: priceId }],
      payment_behavior: 'default_incomplete',
      expand: ['latest_invoice.payment_intent'],
      discounts: couponId ? [{ coupon: couponId }] : undefined,
      metadata: { userId, tier },
    } as any);

    const invoice = subscription.latest_invoice as Stripe.Invoice;
    const paymentIntent = (invoice as any)?.payment_intent as Stripe.PaymentIntent;

    return {
      subscriptionId: subscription.id,
      clientSecret: paymentIntent?.client_secret,
      status: subscription.status,
    };
  }

  async cancelSubscription(subscriptionId: string) {
    return this.stripe.subscriptions.update(subscriptionId, { cancel_at_period_end: true });
  }

  async changeTier(subscriptionId: string, newTier: TierName) {
    const sub = await this.stripe.subscriptions.retrieve(subscriptionId);
    const priceId = process.env[`STRIPE_PRICE_${newTier.toUpperCase()}`] || '';
    return this.stripe.subscriptions.update(subscriptionId, {
      items: [{ id: sub.items.data[0].id, price: priceId }],
      proration_behavior: 'create_prorations',
    });
  }

  private async getOrCreateCustomer(userId: string, email: string) {
    const existing = await this.stripe.customers.list({ email, limit: 1 });
    if (existing.data.length > 0) return existing.data[0];
    return this.stripe.customers.create({ email, metadata: { userId } });
  }

  calculateDiscountedPrice(tier: TierName, discountPercent: number): number {
    return Math.round(TIERS[tier].price * (1 - discountPercent / 100) * 100) / 100;
  }
}

export const subscriptionService = new SubscriptionService();
