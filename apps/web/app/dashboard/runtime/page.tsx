'use client';
import { useState } from 'react';
import Link from 'next/link';

interface RuntimeInstance {
  id: string;
  contractAddress: string;
  status: string;
  riskScore: number;
  lastActivity: string;
}

export default function RuntimePage() {
  const [instances, setInstances] = useState<RuntimeInstance[]>([
    { id: 'rf-001', contractAddress: '0x1234...abcd', status: 'active', riskScore: 15, lastActivity: '2 min ago' },
    { id: 'rf-002', contractAddress: '0x5678...efgh', status: 'monitoring', riskScore: 45, lastActivity: '5 min ago' },
  ]);
  const [newContract, setNewContract] = useState('');
  const [deploying, setDeploying] = useState(false);

  const deployInstance = async () => {
    if (!newContract) return;
    setDeploying(true);
    try {
      const res = await fetch('/api/runtime/status');
      const newInstance: RuntimeInstance = {
        id: 'rf-' + Date.now().toString(36),
        contractAddress: newContract,
        status: 'pending',
        riskScore: 0,
        lastActivity: 'Just now'
      };
      setInstances([newInstance, ...instances]);
      setNewContract('');
    } catch (err) {
      console.error('Deployment failed:', err);
    } finally {
      setDeploying(false);
    }
  };

  const killInstance = async (id: string) => {
    if (!confirm('Terminate this Runtime Fence instance?')) return;
    try {
      await fetch('/api/runtime/kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentId: id, reason: 'Manual termination' })
      });
      setInstances(instances.map(i => i.id === id ? { ...i, status: 'terminated' } : i));
    } catch (err) {
      console.error('Kill failed:', err);
    }
  };

  const getRiskColor = (score: number) => {
    if (score < 25) return 'text-green-500';
    if (score < 50) return 'text-yellow-500';
    if (score < 75) return 'text-orange-500';
    return 'text-red-500';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'monitoring': return 'bg-blue-500';
      case 'pending': return 'bg-yellow-500';
      case 'terminated': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <nav className="flex justify-between items-center p-6 border-b border-gray-800">
        <Link href="/" className="text-2xl font-bold text-red-500">KILLSWITCH</Link>
        <div className="flex gap-4">
          <Link href="/dashboard" className="text-gray-400 hover:text-white">Dashboard</Link>
          <Link href="/dashboard/token" className="text-gray-400 hover:text-white">Token</Link>
          <Link href="/dashboard/runtime" className="text-white">Runtime</Link>
          <Link href="/dashboard/audit" className="text-gray-400 hover:text-white">Audit</Link>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-8">Runtime Fence Management</h1>

        <div className="bg-gray-800 rounded-xl p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Deploy New Instance</h2>
          <p className="text-gray-400 text-sm mb-4">
            Deploy a Runtime Fence to monitor and protect your AI agent or smart contract
          </p>
          <div className="flex gap-4">
            <input
              type="text"
              value={newContract}
              onChange={(e) => setNewContract(e.target.value)}
              placeholder="Contract address to monitor (0x...)"
              className="flex-1 bg-gray-700 rounded px-4 py-3"
            />
            <button
              onClick={deployInstance}
              disabled={deploying || !newContract}
              className="bg-red-600 hover:bg-red-700 disabled:opacity-50 px-8 py-3 rounded-lg font-semibold"
            >
              {deploying ? 'Deploying...' : 'Deploy'}
            </button>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">Active Instances</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3">ID</th>
                  <th className="pb-3">Contract</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Risk Score</th>
                  <th className="pb-3">Last Activity</th>
                  <th className="pb-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {instances.map((instance) => (
                  <tr key={instance.id} className="border-b border-gray-700">
                    <td className="py-4 font-mono text-sm">{instance.id}</td>
                    <td className="py-4 font-mono text-sm text-gray-300">{instance.contractAddress}</td>
                    <td className="py-4">
                      <span className={`${getStatusColor(instance.status)} px-2 py-1 rounded text-xs`}>
                        {instance.status}
                      </span>
                    </td>
                    <td className={`py-4 ${getRiskColor(instance.riskScore)}`}>
                      {instance.riskScore}%
                    </td>
                    <td className="py-4 text-gray-400 text-sm">{instance.lastActivity}</td>
                    <td className="py-4">
                      <div className="flex gap-2">
                        <button className="text-blue-400 hover:text-blue-300 text-sm">View</button>
                        {instance.status !== 'terminated' && (
                          <button
                            onClick={() => killInstance(instance.id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            Kill
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-8">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="text-green-500 text-3xl font-bold mb-2">
              {instances.filter(i => i.status === 'active').length}
            </div>
            <div className="text-gray-400">Active Instances</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="text-yellow-500 text-3xl font-bold mb-2">
              {instances.filter(i => i.riskScore > 50).length}
            </div>
            <div className="text-gray-400">High Risk</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="text-red-500 text-3xl font-bold mb-2">
              {instances.filter(i => i.status === 'terminated').length}
            </div>
            <div className="text-gray-400">Terminated</div>
          </div>
        </div>
      </div>
    </main>
  );
}
