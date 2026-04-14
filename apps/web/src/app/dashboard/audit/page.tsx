'use client';
import { useState } from 'react';
import Link from 'next/link';

interface AuditRequest {
  id: string;
  contractAddress: string;
  auditType: string;
  status: string;
  createdAt: string;
}

export default function AuditPage() {
  const [audits, setAudits] = useState<AuditRequest[]>([]);
  const [contractAddress, setContractAddress] = useState('');
  const [auditType, setAuditType] = useState('basic');
  const [loading, setLoading] = useState(false);

  const submitAudit = async () => {
    if (!contractAddress) return;
    setLoading(true);
    try {
      const res = await fetch('/api/audit/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contractAddress, auditType, requesterId: 1 })
      });
      const data = await res.json();
      setAudits([data.audit, ...audits]);
      setContractAddress('');
    } catch (err) {
      console.error('Failed to submit audit:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete': return 'bg-green-500';
      case 'in_progress': return 'bg-yellow-500';
      case 'pending': return 'bg-blue-500';
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
          <Link href="/dashboard/runtime" className="text-gray-400 hover:text-white">Runtime</Link>
          <Link href="/dashboard/audit" className="text-white">Audit</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-8">Smart Contract Audit</h1>

        <div className="bg-gray-800 rounded-xl p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Request Audit</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-2">Contract Address</label>
              <input
                type="text"
                value={contractAddress}
                onChange={(e) => setContractAddress(e.target.value)}
                placeholder="0x..."
                className="w-full bg-gray-700 rounded px-4 py-3"
              />
            </div>
            <div>
              <label className="block text-gray-400 text-sm mb-2">Audit Type</label>
              <select
                value={auditType}
                onChange={(e) => setAuditType(e.target.value)}
                className="w-full bg-gray-700 rounded px-4 py-3"
              >
                <option value="basic">Basic - Surface level analysis</option>
                <option value="comprehensive">Comprehensive - Deep analysis</option>
                <option value="emergency">Emergency - Priority 24hr turnaround</option>
              </select>
            </div>
            <div className="bg-gray-700 rounded p-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Estimated Cost</span>
                <span>{auditType === 'basic' ? '100' : auditType === 'comprehensive' ? '500' : '1000'} $KILLSWITCH</span>
              </div>
              <div className="flex justify-between text-sm mt-2">
                <span className="text-gray-400">Estimated Time</span>
                <span>{auditType === 'basic' ? '3-5 days' : auditType === 'comprehensive' ? '7-14 days' : '24 hours'}</span>
              </div>
            </div>
            <button
              onClick={submitAudit}
              disabled={loading || !contractAddress}
              className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 px-6 py-3 rounded-lg font-semibold"
            >
              {loading ? 'Submitting...' : 'Submit Audit Request'}
            </button>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">Your Audit Requests</h2>
          {audits.length === 0 ? (
            <p className="text-gray-400 text-center py-8">No audit requests yet</p>
          ) : (
            <div className="space-y-4">
              {audits.map((audit) => (
                <div key={audit.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-mono text-sm text-gray-300">{audit.contractAddress}</div>
                      <div className="text-gray-400 text-sm mt-1">{audit.auditType} audit</div>
                    </div>
                    <span className={`${getStatusColor(audit.status)} px-3 py-1 rounded text-xs`}>
                      {audit.status}
                    </span>
                  </div>
                  <div className="text-gray-500 text-xs mt-2">ID: {audit.id}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
