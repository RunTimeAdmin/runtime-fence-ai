'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import { api } from '../../lib/api';

interface Agent {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'killed';
  last_activity: number | string;
  api_calls_today: number;
  created_at: number | string;
  user_id?: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [registerName, setRegisterName] = useState('');
  const [registering, setRegistering] = useState(false);

  const fetchAgents = useCallback(async () => {
    setError(null);
    
    try {
      const { data, error: fetchError } = await supabase
        .from('agents')
        .select('*')
        .order('created_at', { ascending: false });

      if (fetchError) {
        console.error('Failed to fetch agents:', fetchError);
        setError('Failed to load agents');
        return;
      }

      setAgents((data || []).map(a => ({
        id: a.id,
        name: a.name,
        status: a.status,
        last_activity: a.last_activity || Date.now(),
        api_calls_today: a.api_calls_today || 0,
        created_at: a.created_at,
        user_id: a.user_id
      })));
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError('Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const toggleAgent = async (agentId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    
    try {
      const { error: updateError } = await supabase
        .from('agents')
        .update({ status: newStatus, updated_at: Date.now() })
        .eq('id', agentId);

      if (updateError) {
        console.error('Failed to update agent:', updateError);
        alert('Failed to update agent status');
        return;
      }

      setAgents(prev => prev.map(a => 
        a.id === agentId ? { ...a, status: newStatus as Agent['status'] } : a
      ));
    } catch (err) {
      console.error('Failed to update agent:', err);
      alert('Failed to update agent status');
    }
  };

  const killAgent = async (agentId: string) => {
    if (!confirm('Are you sure you want to kill this agent?')) return;

    try {
      // Update agent status
      const { error: updateError } = await supabase
        .from('agents')
        .update({ status: 'killed', updated_at: Date.now() })
        .eq('id', agentId);

      if (updateError) {
        console.error('Failed to kill agent:', updateError);
        alert('Failed to kill agent');
        return;
      }

      // Insert kill signal record
      const agent = agents.find(a => a.id === agentId);
      await supabase
        .from('kill_signals')
        .insert({
          id: `kill-${Date.now()}`,
          agent_id: agentId,
          reason: 'Manual kill from dashboard',
          triggered_by: 'user',
          created_at: Date.now()
        });

      setAgents(prev => prev.map(a => 
        a.id === agentId ? { ...a, status: 'killed' } : a
      ));
    } catch (err) {
      console.error('Failed to kill agent:', err);
      alert('Failed to kill agent');
    }
  };

  const registerAgent = async () => {
    if (!registerName.trim()) {
      alert('Please enter an agent name');
      return;
    }

    setRegistering(true);
    
    try {
      const agentId = `agent-${Date.now().toString(36)}`;
      
      // Try API first, fallback to direct Supabase insert
      try {
        await api.post('/api/v1/agents', {
          id: agentId,
          name: registerName,
          status: 'active'
        });
      } catch {
        // Fallback to direct Supabase insert
        const { error: insertError } = await supabase
          .from('agents')
          .insert({
            id: agentId,
            name: registerName,
            status: 'active',
            user_id: 'current-user', // Should be replaced with actual user ID
            api_calls_today: 0,
            created_at: Date.now()
          });

        if (insertError) {
          throw insertError;
        }
      }

      setRegisterName('');
      await fetchAgents();
    } catch (err) {
      console.error('Failed to register agent:', err);
      alert('Failed to register agent');
    } finally {
      setRegistering(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'paused': return 'bg-yellow-500';
      case 'killed': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Live Status Banner */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white text-center py-2 px-4 text-sm">
        <span className="font-semibold">🟢 Live</span> — Manage your agents. <a href="/docs" className="underline">API docs</a>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">
            <span className="text-red-500">Agent</span> Dashboard
          </h1>
          <div className="flex gap-4">
            <a href="/" className="text-gray-400 hover:text-white">← Home</a>
            <a href="/dashboard/live" className="text-gray-400 hover:text-white">Live Activity</a>
            <a href="/governance" className="text-gray-400 hover:text-white">Governance</a>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-6">
            {error}
            <button 
              onClick={fetchAgents}
              className="ml-4 underline hover:text-white"
            >
              Retry
            </button>
          </div>
        )}

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-sm">Total Agents</p>
            <p className="text-2xl font-bold">{agents.length}</p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-sm">Active</p>
            <p className="text-2xl font-bold text-green-400">
              {agents.filter(a => a.status === 'active').length}
            </p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-sm">Paused</p>
            <p className="text-2xl font-bold text-yellow-400">
              {agents.filter(a => a.status === 'paused').length}
            </p>
          </div>
          <div className="bg-gray-900 p-4 rounded-lg border border-gray-800">
            <p className="text-gray-400 text-sm">API Calls Today</p>
            <p className="text-2xl font-bold">
              {agents.reduce((sum, a) => sum + a.api_calls_today, 0)}
            </p>
          </div>
        </div>

        {/* Agents List */}
        <h2 className="text-xl font-semibold mb-4">Your Agents</h2>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
          </div>
        ) : agents.length === 0 ? (
          <div className="bg-gray-900 p-8 rounded-lg border border-gray-800 text-center">
            <p className="text-gray-400 mb-4">No agents registered yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            {agents.map((agent) => (
              <div key={agent.id} className="bg-gray-900 p-6 rounded-lg border border-gray-800">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${getStatusColor(agent.status)}`} />
                    <div>
                      <h3 className="text-lg font-semibold">{agent.name}</h3>
                      <p className="text-gray-400 text-sm">
                        Last active: {new Date(agent.last_activity).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${getStatusColor(agent.status)}`}>
                    {agent.status.toUpperCase()}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 mt-4 text-sm">
                  <div>
                    <p className="text-gray-400">API Calls Today</p>
                    <p className="font-semibold">{agent.api_calls_today}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">Registered</p>
                    <p className="font-semibold">
                      {typeof agent.created_at === 'number' 
                        ? new Date(agent.created_at).toLocaleDateString() 
                        : agent.created_at}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-400">ID</p>
                    <p className="font-mono text-xs">{agent.id}</p>
                  </div>
                </div>

                <div className="flex gap-2 mt-4">
                  {agent.status !== 'killed' && (
                    <>
                      <button
                        onClick={() => toggleAgent(agent.id, agent.status)}
                        className={`px-4 py-2 rounded text-sm ${
                          agent.status === 'active' 
                            ? 'bg-yellow-600 hover:bg-yellow-700' 
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {agent.status === 'active' ? 'Pause' : 'Resume'}
                      </button>
                      <button
                        onClick={() => killAgent(agent.id)}
                        className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded text-sm"
                      >
                        Kill
                      </button>
                    </>
                  )}
                  <button className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded text-sm">
                    View Logs
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Register New Agent CTA */}
        <div className="mt-8 p-6 bg-gray-900 rounded-lg border border-gray-800">
          <h3 className="text-lg font-semibold mb-2">Register a New Agent</h3>
          <p className="text-gray-400 text-sm mb-4">
            Add the Killswitch fence to your AI agent for real-time monitoring and control.
          </p>
          
          <div className="flex gap-4 mb-4">
            <input
              type="text"
              value={registerName}
              onChange={(e) => setRegisterName(e.target.value)}
              placeholder="Enter agent name..."
              className="flex-1 bg-black border border-gray-700 rounded px-4 py-2 text-white placeholder-gray-500"
              disabled={registering}
            />
            <button
              onClick={registerAgent}
              disabled={registering || !registerName.trim()}
              className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-6 py-2 rounded font-semibold"
            >
              {registering ? 'Registering...' : 'Register'}
            </button>
          </div>
          
          <code className="block bg-black p-4 rounded text-sm text-green-400 mb-4">
            pip install killswitch-fence
          </code>
          <a href="/docs" className="text-red-400 hover:text-red-300 text-sm">
            View Integration Guide →
          </a>
        </div>
      </div>
    </main>
  );
}