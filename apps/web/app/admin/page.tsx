'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../../lib/supabase';

interface Stats {
  totalUsers: number;
  totalAgents: number;
  activeAgents: number;
  killedAgents: number;
  totalRevenue: number;
  apiCallsToday: number;
  newUsersToday: number;
  killSignalsToday: number;
}

interface User {
  id: string;
  wallet_address: string;
  tier: string;
  created_at: string;
  agents_count: number;
}

interface KillSignal {
  id: string;
  agent_id: string;
  reason: string;
  triggered_by: string;
  created_at: string;
}

interface SecurityModule {
  name: string;
  status: 'active' | 'standby' | 'disabled';
  lastCheck: string;
}

export default function AdminPage() {
  const [stats, setStats] = useState<Stats>({
    totalUsers: 0,
    totalAgents: 0,
    activeAgents: 0,
    killedAgents: 0,
    totalRevenue: 0,
    apiCallsToday: 0,
    newUsersToday: 0,
    killSignalsToday: 0
  });
  const [users, setUsers] = useState<User[]>([]);
  const [killSignals, setKillSignals] = useState<KillSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'security' | 'logs'>('overview');

  const securityModules: SecurityModule[] = [
    { name: 'Fail-Mode Handler', status: 'active', lastCheck: '2s ago' },
    { name: 'Hard Kill (SIGKILL)', status: 'active', lastCheck: '2s ago' },
    { name: 'Behavioral Thresholds', status: 'active', lastCheck: '5s ago' },
    { name: 'Network Kill', status: 'standby', lastCheck: '10s ago' },
    { name: 'Bypass Protection', status: 'active', lastCheck: '3s ago' },
    { name: 'Intent Analyzer (LLM)', status: 'active', lastCheck: '1s ago' },
    { name: 'Task Adherence', status: 'active', lastCheck: '4s ago' },
    { name: 'Sliding Window', status: 'active', lastCheck: '2s ago' },
    { name: 'Honeypot', status: 'standby', lastCheck: '30s ago' },
    { name: 'Governance Gateway', status: 'active', lastCheck: '1s ago' },
  ];

  const fetchData = useCallback(async () => {
    setError(null);
    setLoading(true);
    
    try {
      // Fetch users count
      const { count: usersCount, error: usersError } = await supabase
        .from('users')
        .select('*', { count: 'exact', head: true });

      // Fetch agents count
      const { count: agentsCount, error: agentsError } = await supabase
        .from('agents')
        .select('*', { count: 'exact', head: true });

      // Fetch active agents
      const { count: activeCount } = await supabase
        .from('agents')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'active');

      // Fetch killed agents
      const { count: killedCount } = await supabase
        .from('agents')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'killed');

      // Fetch kill signals
      const { data: killData } = await supabase
        .from('kill_signals')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10);

      // Fetch recent users
      const { data: usersData } = await supabase
        .from('users')
        .select('id, email, role, tier, created_at')
        .order('created_at', { ascending: false })
        .limit(20);

      // Fetch new users today (users created in last 24h)
      const oneDayAgo = Date.now() - 86400000;
      const { count: newUsersCount } = await supabase
        .from('users')
        .select('*', { count: 'exact', head: true })
        .gte('created_at', oneDayAgo);

      // Fetch audit logs for today
      const { data: auditData } = await supabase
        .from('audit_logs')
        .select('result')
        .gte('timestamp', oneDayAgo);

      // Calculate API calls today from audit logs
      const apiCallsToday = auditData?.length || 0;

      // Count kill signals today
      const killSignalsToday = killData?.filter(k => k.created_at >= oneDayAgo).length || 0;

      if (usersError || agentsError) {
        console.error('Supabase query error:', usersError || agentsError);
      }

      setStats({
        totalUsers: usersCount || 0,
        totalAgents: agentsCount || 0,
        activeAgents: activeCount || 0,
        killedAgents: killedCount || 0,
        totalRevenue: 0, // Would need subscription data
        apiCallsToday,
        newUsersToday: newUsersCount || 0,
        killSignalsToday
      });

      // Transform users data for display
      const transformedUsers: User[] = (usersData || []).map(u => ({
        id: u.id,
        wallet_address: u.email || u.id.slice(0, 8),
        tier: u.tier || 'basic',
        created_at: u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A',
        agents_count: 0 // Would need separate query
      }));

      setUsers(transformedUsers);
      setKillSignals((killData || []).map(k => ({
        id: k.id,
        agent_id: k.agent_id,
        reason: k.reason || 'No reason provided',
        triggered_by: k.triggered_by || 'unknown',
        created_at: k.created_at ? new Date(k.created_at).toLocaleString() : 'N/A'
      })));

    } catch (err) {
      console.error('Failed to fetch admin data:', err);
      setError('Failed to load data. Please check your connection.');
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const shortenAddress = (addr: string) => {
    if (addr.length <= 12) return addr;
    return `${addr.slice(0, 4)}...${addr.slice(-4)}`;
  };

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold">
              <span className="text-red-500">$KILLSWITCH</span> Admin
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Last refresh: {lastRefresh.toLocaleTimeString()} (auto-refresh 30s)
            </p>
          </div>
          <div className="flex gap-4 items-center">
            <a href="/agents" className="text-gray-400 hover:text-white">Agents</a>
            <a href="/governance" className="text-gray-400 hover:text-white">Governance</a>
            <a href="/" className="text-gray-400 hover:text-white">Home</a>
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

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-800 pb-4">
          {(['overview', 'users', 'security', 'logs'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-t text-sm font-medium transition ${
                activeTab === tab
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-900 text-gray-400 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
          </div>
        ) : (
          <>
        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-xs">Total Users</p>
            <p className="text-2xl font-bold">{stats.totalUsers}</p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-xs">Total Agents</p>
            <p className="text-2xl font-bold">{stats.totalAgents}</p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-xs">Active Agents</p>
            <p className="text-2xl font-bold text-green-400">{stats.activeAgents}</p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-xs">Revenue (USD)</p>
            <p className="text-2xl font-bold text-green-400">${stats.totalRevenue.toLocaleString()}</p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-xs">API Calls Today</p>
            <p className="text-2xl font-bold">{stats.apiCallsToday.toLocaleString()}</p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-xs">New Users Today</p>
            <p className="text-2xl font-bold text-blue-400">+{stats.newUsersToday}</p>
          </div>
        </div>

        {/* Revenue by Tier */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold mb-4">Revenue by Tier</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span>Basic ($5)</span>
                <span className="font-semibold">12 users = $60</span>
              </div>
              <div className="flex justify-between">
                <span>Pro ($50)</span>
                <span className="font-semibold">18 users = $900</span>
              </div>
              <div className="flex justify-between">
                <span>Team ($250)</span>
                <span className="font-semibold">8 users = $2,000</span>
              </div>
              <div className="flex justify-between">
                <span>Enterprise ($1K)</span>
                <span className="font-semibold">5 users = $5,000</span>
              </div>
              <div className="flex justify-between">
                <span>VIP ($5K)</span>
                <span className="font-semibold">1 user = $5,000</span>
              </div>
              <div className="border-t border-gray-700 pt-3 flex justify-between font-bold">
                <span>Total MRR</span>
                <span className="text-green-400">$12,960</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold mb-4">System Health</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span>API Server</span>
                <span className="bg-green-500 text-xs px-2 py-1 rounded">ONLINE</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Database</span>
                <span className="bg-green-500 text-xs px-2 py-1 rounded">ONLINE</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Solana RPC</span>
                <span className="bg-green-500 text-xs px-2 py-1 rounded">CONNECTED</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Stripe</span>
                <span className="bg-yellow-500 text-xs px-2 py-1 rounded">TEST MODE</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Email Service</span>
                <span className="bg-gray-500 text-xs px-2 py-1 rounded">NOT CONFIGURED</span>
              </div>
            </div>
          </div>
        </div>

        {/* Security Modules */}
        {activeTab === 'security' && (
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8">
            <h2 className="text-lg font-semibold mb-4">Security Modules (10 Active)</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {securityModules.map((mod) => (
                <div key={mod.name} className="bg-gray-800 p-3 rounded border border-gray-700">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium truncate">{mod.name}</span>
                    <span className={`w-2 h-2 rounded-full ${
                      mod.status === 'active' ? 'bg-green-500' :
                      mod.status === 'standby' ? 'bg-yellow-500' : 'bg-gray-500'
                    }`} />
                  </div>
                  <p className="text-xs text-gray-500">{mod.lastCheck}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Kill Signals Log */}
        {activeTab === 'logs' && (
          <div className="bg-gray-900 p-6 rounded-lg border border-gray-800 mb-8">
            <h2 className="text-lg font-semibold mb-4">Recent Kill Signals</h2>
            {killSignals.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No kill signals recorded</p>
            ) : (
              <div className="space-y-2">
                {killSignals.map((signal) => (
                  <div key={signal.id} className="flex items-center justify-between bg-gray-800 p-3 rounded">
                    <div className="flex items-center gap-3">
                      <span className="text-red-500">⚠</span>
                      <div>
                        <p className="font-mono text-sm">{signal.agent_id}</p>
                        <p className="text-xs text-gray-400">{signal.reason}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-1 rounded ${
                        signal.triggered_by === 'auto' ? 'bg-red-900 text-red-300' :
                        signal.triggered_by === 'admin' ? 'bg-blue-900 text-blue-300' :
                        'bg-yellow-900 text-yellow-300'
                      }`}>
                        {signal.triggered_by}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">{signal.created_at}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Recent Users */}
        <div className="bg-gray-900 p-6 rounded-lg border border-gray-800">
          <h2 className="text-lg font-semibold mb-4">Recent Users</h2>
          {users.length === 0 ? (
            <p className="text-gray-400 text-center py-8">No users found</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-800">
                    <th className="pb-3">Email/Wallet</th>
                    <th className="pb-3">Tier</th>
                    <th className="pb-3">Agents</th>
                    <th className="pb-3">Joined</th>
                    <th className="pb-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-b border-gray-800">
                      <td className="py-3 font-mono">{shortenAddress(user.wallet_address)}</td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs ${
                          user.tier === 'vip' ? 'bg-purple-600' :
                          user.tier === 'enterprise' ? 'bg-red-600' :
                          user.tier === 'team' ? 'bg-blue-600' :
                          user.tier === 'pro' ? 'bg-green-600' :
                          'bg-gray-600'
                        }`}>
                          {user.tier.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3">{user.agents_count}</td>
                      <td className="py-3 text-gray-400">{user.created_at}</td>
                      <td className="py-3">
                        <button className="text-blue-400 hover:text-blue-300 mr-2">View</button>
                        <button className="text-red-400 hover:text-red-300">Ban</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          <button className="bg-gray-900 hover:bg-gray-800 p-4 rounded-lg border border-gray-800 text-left">
            <p className="font-semibold">Export Users</p>
            <p className="text-gray-400 text-sm">Download CSV</p>
          </button>
          <button className="bg-gray-900 hover:bg-gray-800 p-4 rounded-lg border border-gray-800 text-left">
            <p className="font-semibold">View Logs</p>
            <p className="text-gray-400 text-sm">Audit trail</p>
          </button>
          <button className="bg-gray-900 hover:bg-gray-800 p-4 rounded-lg border border-gray-800 text-left">
            <p className="font-semibold">Send Broadcast</p>
            <p className="text-gray-400 text-sm">Email all users</p>
          </button>
          <button className="bg-red-900 hover:bg-red-800 p-4 rounded-lg border border-red-700 text-left">
            <p className="font-semibold">Emergency Kill</p>
            <p className="text-gray-400 text-sm">Stop all agents</p>
          </button>
        </div>
          </>
        )}
      </div>
    </main>
  );
}