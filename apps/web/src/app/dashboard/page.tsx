'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Agent { id: string; name: string; status: string; riskLevel: string; }
interface Stats { totalAgents: number; activeAgents: number; triggeredToday: number; avgRiskScore: number; }

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([
    { id: 'agent-001', name: 'Trading Bot Alpha', status: 'active', riskLevel: 'low' },
    { id: 'agent-002', name: 'Data Processor', status: 'active', riskLevel: 'medium' },
    { id: 'agent-003', name: 'Market Analyzer', status: 'suspended', riskLevel: 'high' },
  ]);
  const [stats, setStats] = useState<Stats>({ totalAgents: 3, activeAgents: 2, triggeredToday: 1, avgRiskScore: 35 });
  const [globalKill, setGlobalKill] = useState(false);

  const getRiskColor = (level: string) => {
    switch(level) { case 'low': return 'text-green-500'; case 'medium': return 'text-yellow-500'; case 'high': return 'text-orange-500'; default: return 'text-red-500'; }
  };
  const getStatusColor = (status: string) => status === 'active' ? 'bg-green-500' : status === 'suspended' ? 'bg-red-500' : 'bg-gray-500';

  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <nav className="flex justify-between items-center p-6 border-b border-gray-800">
        <Link href="/" className="text-2xl font-bold text-red-500">KILLSWITCH</Link>
        <div className="flex gap-4 items-center">
          <span className={globalKill ? 'text-red-500 animate-pulse' : 'text-green-500'}>
            {globalKill ? 'GLOBAL KILL ACTIVE' : 'System Normal'}
          </span>
          <button onClick={() => setGlobalKill(!globalKill)} className={globalKill ? 'bg-green-600 px-4 py-2 rounded' : 'bg-red-600 px-4 py-2 rounded'}>
            {globalKill ? 'Reset System' : 'Emergency Kill'}
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-xl">
            <div className="text-gray-400 text-sm">Total Agents</div>
            <div className="text-3xl font-bold">{stats.totalAgents}</div>
          </div>
          <div className="bg-gray-800 p-6 rounded-xl">
            <div className="text-gray-400 text-sm">Active Agents</div>
            <div className="text-3xl font-bold text-green-500">{stats.activeAgents}</div>
          </div>
          <div className="bg-gray-800 p-6 rounded-xl">
            <div className="text-gray-400 text-sm">Triggered Today</div>
            <div className="text-3xl font-bold text-red-500">{stats.triggeredToday}</div>
          </div>
          <div className="bg-gray-800 p-6 rounded-xl">
            <div className="text-gray-400 text-sm">Avg Risk Score</div>
            <div className="text-3xl font-bold text-yellow-500">{stats.avgRiskScore}%</div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">Registered Agents</h2>
          <table className="w-full">
            <thead><tr className="text-left text-gray-400 border-b border-gray-700">
              <th className="pb-3">ID</th><th className="pb-3">Name</th><th className="pb-3">Status</th><th className="pb-3">Risk</th><th className="pb-3">Actions</th>
            </tr></thead>
            <tbody>
              {agents.map(agent => (
                <tr key={agent.id} className="border-b border-gray-700">
                  <td className="py-4 font-mono text-sm">{agent.id}</td>
                  <td className="py-4">{agent.name}</td>
                  <td className="py-4"><span className={getStatusColor(agent.status) + ' px-2 py-1 rounded text-xs'}>{agent.status}</span></td>
                  <td className={'py-4 ' + getRiskColor(agent.riskLevel)}>{agent.riskLevel}</td>
                  <td className="py-4"><button className="text-red-400 hover:text-red-300 text-sm">Kill</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
