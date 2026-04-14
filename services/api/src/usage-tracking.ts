/**
 * $KILLSWITCH Usage Tracking Middleware
 * Track API calls and enforce tier limits
 */
import { Request, Response, NextFunction } from 'express';
import { TIERS, TierName } from './subscription-service';
import { supabase, isSupabaseConfigured } from './db';

// In-memory usage tracking (fallback when Supabase is not configured)
const usageCache: Map<string, { count: number; periodStart: Date }> = new Map();

export interface UsageInfo {
  userId: string;
  tier: TierName;
  apiCallsUsed: number;
  apiCallsLimit: number;
  percentUsed: number;
}

/**
 * Get current billing period start
 */
function getPeriodStart(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1);
}

/**
 * Get usage for a user
 */
export async function getUsage(userId: string): Promise<{ count: number; periodStart: Date }> {
  const periodStart = getPeriodStart();
  const periodStartStr = periodStart.toISOString().split('T')[0]; // YYYY-MM-DD

  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('usage_tracking')
      .select('*')
      .eq('user_id', userId)
      .eq('period_start', periodStartStr)
      .single();
    
    if (error && error.code !== 'PGRST116') {
      console.error('Failed to fetch usage from Supabase:', error);
    }
    
    if (data) {
      return {
        count: data.api_calls_used,
        periodStart: new Date(data.period_start)
      };
    }
    
    // No usage record yet for this period
    return { count: 0, periodStart };
  }

  // Fallback to in-memory
  const key = userId;

  const cached = usageCache.get(key);
  if (cached && cached.periodStart.getTime() === periodStart.getTime()) {
    return cached;
  }

  // Reset for new period
  const usage = { count: 0, periodStart };
  usageCache.set(key, usage);
  return usage;
}

/**
 * Increment usage
 */
export async function incrementUsage(userId: string): Promise<number> {
  const periodStart = getPeriodStart();
  const periodStartStr = periodStart.toISOString().split('T')[0];
  const now = Date.now();

  if (isSupabaseConfigured()) {
    // Try to update existing record first
    const { data: existing, error: fetchError } = await supabase
      .from('usage_tracking')
      .select('api_calls_used')
      .eq('user_id', userId)
      .eq('period_start', periodStartStr)
      .single();
    
    if (fetchError && fetchError.code !== 'PGRST116') {
      console.error('Failed to fetch usage for increment:', fetchError);
    }
    
    if (existing) {
      // Update existing
      const newCount = existing.api_calls_used + 1;
      const { error: updateError } = await supabase
        .from('usage_tracking')
        .update({ 
          api_calls_used: newCount,
          updated_at: now
        })
        .eq('user_id', userId)
        .eq('period_start', periodStartStr);
      
      if (updateError) {
        console.error('Failed to increment usage in Supabase:', updateError);
      }
      
      return newCount;
    } else {
      // Insert new
      const { error: insertError } = await supabase
        .from('usage_tracking')
        .insert({
          user_id: userId,
          period_start: periodStartStr,
          api_calls_used: 1,
          updated_at: now
        });
      
      if (insertError) {
        console.error('Failed to insert usage in Supabase:', insertError);
      }
      
      return 1;
    }
  }

  // Fallback to in-memory
  const usage = await getUsage(userId);
  usage.count++;
  usageCache.set(userId, usage);
  return usage.count;
}

/**
 * Check if user is within limits
 */
export async function checkLimit(userId: string, tier: TierName): Promise<boolean> {
  const limit = TIERS[tier].apiCalls;
  if (limit === -1) return true; // Unlimited

  const usage = await getUsage(userId);
  return usage.count < limit;
}

/**
 * Get usage info for user
 */
export async function getUsageInfo(userId: string, tier: TierName): Promise<UsageInfo> {
  const usage = await getUsage(userId);
  const limit = TIERS[tier].apiCalls;

  return {
    userId,
    tier,
    apiCallsUsed: usage.count,
    apiCallsLimit: limit,
    percentUsed: limit === -1 ? 0 : Math.round((usage.count / limit) * 100),
  };
}

/**
 * Usage tracking middleware
 */
export function trackUsage(metricType: string = 'api_calls') {
  return async (req: Request, res: Response, next: NextFunction) => {
    const user = (req as any).user;
    if (!user) return next();

    const userId = user.id;
    const tier = (user.tier || 'basic') as TierName;

    // Check limits before processing
    if (!(await checkLimit(userId, tier))) {
      return res.status(429).json({
        error: 'Rate limit exceeded',
        message: `You have exceeded your ${tier} tier limit of ${TIERS[tier as keyof typeof TIERS].apiCalls} API calls per month`,
        upgrade: 'Upgrade your plan at /settings/subscription',
      });
    }

    // Track the request
    const newCount = await incrementUsage(userId);

    // Add usage headers
    const limit = TIERS[tier as keyof typeof TIERS].apiCalls;
    res.setHeader('X-Usage-Count', newCount.toString());
    res.setHeader('X-Usage-Limit', limit === -1 ? 'unlimited' : limit.toString());
    res.setHeader('X-Usage-Remaining', limit === -1 ? 'unlimited' : (limit - newCount).toString());

    // Warn when approaching limit
    if (limit !== -1 && newCount >= limit * 0.8) {
      res.setHeader('X-Usage-Warning', 'Approaching rate limit');
    }

    next();
  };
}

/**
 * Agent limit middleware
 */
export function checkAgentLimit(tier: TierName, currentAgents: number): boolean {
  const limit = TIERS[tier].agents;
  if (limit === -1) return true; // Unlimited
  return currentAgents < limit;
}

/**
 * Storage limit middleware
 */
export function checkStorageLimit(tier: TierName, currentStorageGb: number): boolean {
  const limit = TIERS[tier].storageGb;
  if (limit === -1) return true; // Unlimited
  return currentStorageGb < limit;
}

/**
 * Reset usage (for testing)
 */
export async function resetUsage(userId: string): Promise<void> {
  const periodStart = getPeriodStart();
  const periodStartStr = periodStart.toISOString().split('T')[0];

  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('usage_tracking')
      .delete()
      .eq('user_id', userId)
      .eq('period_start', periodStartStr);
    
    if (error) {
      console.error('Failed to reset usage in Supabase:', error);
    }
  }

  // Fallback to in-memory
  usageCache.delete(userId);
}

/**
 * Get all usage stats (admin)
 */
export async function getAllUsageStats(): Promise<Map<string, { count: number; periodStart: Date }>> {
  if (isSupabaseConfigured()) {
    const periodStart = getPeriodStart();
    const periodStartStr = periodStart.toISOString().split('T')[0];
    
    const { data, error } = await supabase
      .from('usage_tracking')
      .select('*')
      .eq('period_start', periodStartStr);
    
    if (error) {
      console.error('Failed to fetch all usage stats from Supabase:', error);
      return new Map();
    }
    
    const result = new Map<string, { count: number; periodStart: Date }>();
    for (const row of (data || [])) {
      result.set(row.user_id, {
        count: row.api_calls_used,
        periodStart: new Date(row.period_start)
      });
    }
    
    return result;
  }

  // Fallback to in-memory
  return new Map(usageCache);
}
