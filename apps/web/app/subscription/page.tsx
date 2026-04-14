'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import { api } from '../../lib/api';

interface Subscription {
  tier: string;
  status: string;
  current_period_end: string;
  api_calls_used: number;
  api_calls_limit: number;
  agents_used: number;
  agents_limit: number;
}

interface UserData {
  id: string;
  email: string;
  tier: string;
  role: string;
}

const TIERS = [
  { name: 'Basic', price: 5, agents: 1, apiCalls: 10, features: ['1 Agent', 'Dashboard access', 'Email support'] },
  { name: 'Pro', price: 50, agents: 3, apiCalls: 100, features: ['3 Agents', '100 API calls/day', 'Priority support'] },
  { name: 'Team', price: 250, agents: 10, apiCalls: 1000, features: ['10 Agents', '1K API calls/day', 'Team dashboard'] },
  { name: 'Enterprise', price: 1000, agents: -1, apiCalls: 10000, features: ['Unlimited Agents', '10K API calls/day', 'Dedicated support'] },
  { name: 'VIP', price: 5000, agents: -1, apiCalls: -1, features: ['Unlimited Everything', 'Custom integrations', '24/7 hotline'] }
];

export default function SubscriptionPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setError(null);
    
    try {
      // Check for stored user
      const storedUser = typeof window !== 'undefined' 
        ? localStorage.getItem('killswitch_user')
        : null;
      
      let userData: UserData | null = null;
      
      if (storedUser) {
        userData = JSON.parse(storedUser);
        setUser(userData);
      }

      // Try to get user from API
      try {
        const meResponse = await api.get<UserData>('/api/auth/me');
        setUser(meResponse);
        userData = meResponse;
      } catch {
        // Not authenticated, use stored user or default
        if (!userData) {
          userData = { id: 'anonymous', email: 'anonymous', tier: 'free', role: 'user' };
        }
      }

      // Fetch usage data from Supabase
      let apiCallsUsed = 0;
      let agentsUsed = 0;

      if (userData && userData.id !== 'anonymous') {
        const now = new Date();
        const periodStart = new Date(now.getFullYear(), now.getMonth(), 1);
        const periodStartStr = periodStart.toISOString().split('T')[0];
        
        // Get usage tracking
        const { data: usageData } = await supabase
          .from('usage_tracking')
          .select('api_calls_used')
          .eq('user_id', userData.id)
          .eq('period_start', periodStartStr)
          .single();
        
        apiCallsUsed = usageData?.api_calls_used || 0;

        // Count agents
        const { count: agentCount } = await supabase
          .from('agents')
          .select('*', { count: 'exact', head: true })
          .eq('user_id', userData.id);
        
        agentsUsed = agentCount || 0;
      }

      // Get tier limits
      const tierName = (userData?.tier || 'free').toLowerCase();
      const tierConfig = TIERS.find(t => t.name.toLowerCase() === tierName) || TIERS[0];

      setSubscription({
        tier: tierName,
        status: 'active',
        current_period_end: '',
        api_calls_used: apiCallsUsed,
        api_calls_limit: tierConfig.apiCalls,
        agents_used: agentsUsed,
        agents_limit: tierConfig.agents
      });

    } catch (err) {
      console.error('Failed to fetch subscription data:', err);
      setError('Failed to load subscription data');
      
      // Set default subscription
      setSubscription({
        tier: 'free',
        status: 'active',
        current_period_end: '',
        api_calls_used: 0,
        api_calls_limit: 10,
        agents_used: 0,
        agents_limit: 1
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUpgrade = (tier: string) => {
    // In production, this would open Stripe checkout
    alert(`Upgrade to ${tier} - Stripe integration coming soon!`);
  };

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Live Status Banner */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white text-center py-2 px-4 text-sm">
        <span className="font-semibold">🟢 Live</span> — Choose a plan to get started. <a href="/docs" className="underline">Test API</a>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">
            <span className="text-red-500">Subscription</span> Management
          </h1>
          <div className="flex gap-4">
            <a href="/" className="text-gray-400 hover:text-white">← Home</a>
            <a href="/agents" className="text-gray-400 hover:text-white">Agents</a>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6">
            {error}
            <button 
              onClick={fetchData}
              className="ml-4 underline hover:text-white"
            >
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
          </div>
        ) : (
          <>
        {/* Current Plan */}
        {subscription && (
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8">
            <h2 className="text-xl font-semibold mb-4">Current Plan</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-gray-400 text-sm">Tier</p>
                <p className="text-2xl font-bold capitalize">{subscription.tier}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Status</p>
                <p className="text-2xl font-bold text-green-400 capitalize">{subscription.status}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">API Usage</p>
                <p className="text-2xl font-bold">
                  {subscription.api_calls_used}/{subscription.api_calls_limit === -1 ? '∞' : subscription.api_calls_limit}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Agents</p>
                <p className="text-2xl font-bold">
                  {subscription.agents_used}/{subscription.agents_limit === -1 ? '∞' : subscription.agents_limit}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Pricing Tiers */}
        <h2 className="text-xl font-semibold mb-4">Available Plans</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {TIERS.map((tier) => (
            <div 
              key={tier.name}
              className={`bg-gray-900 p-6 rounded-lg border ${
                subscription?.tier === tier.name.toLowerCase() 
                  ? 'border-red-500' 
                  : 'border-gray-800'
              }`}
            >
              <h3 className="text-lg font-semibold mb-2">{tier.name}</h3>
              <div className="mb-4">
                <p className="text-2xl font-bold">
                  ${tier.price}
                  <span className="text-sm text-gray-400">/mo</span>
                </p>
              </div>
              <ul className="text-sm text-gray-400 space-y-2 mb-4">
                {tier.features.map((f, i) => (
                  <li key={i}>✓ {f}</li>
                ))}
              </ul>
              {subscription?.tier === tier.name.toLowerCase() ? (
                <button 
                  disabled
                  className="w-full bg-gray-700 text-gray-400 py-2 rounded cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : (
                <button 
                  onClick={() => handleUpgrade(tier.name)}
                  className="w-full bg-red-600 hover:bg-red-700 py-2 rounded font-semibold"
                >
                  Upgrade
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Payment Methods */}
        <div className="mt-8 bg-gray-900 p-6 rounded-lg border border-gray-800">
          <h3 className="text-lg font-semibold mb-4">Payment Methods</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-xl">💳</span>
              <span>Credit Card (Stripe)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xl">◎</span>
              <span>Solana (SOL)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xl">💵</span>
              <span>USDC on Solana</span>
            </div>
          </div>
        </div>
          </>
        )}
      </div>
    </main>
  );
}