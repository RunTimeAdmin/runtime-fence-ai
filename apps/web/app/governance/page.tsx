'use client';

import { useEffect, useState } from 'react';
import { supabase } from '../../lib/supabase';

interface Proposal {
  id: string;
  title: string;
  description: string;
  votes_for: number;
  votes_against: number;
  status: string;
  ends_at: string;
}

export default function GovernancePage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [voting, setVoting] = useState<string | null>(null);

  // Fetch proposals from Supabase
  useEffect(() => {
    async function fetchProposals() {
      const { data, error } = await supabase
        .from('proposals')
        .select('*')
        .eq('status', 'active')
        .order('created_at', { ascending: false });

      if (error) {
        console.error('Error fetching proposals:', error);
        // Use mock data if table doesn't exist yet
        setProposals([
          {
            id: '1',
            title: 'Increase API rate limits for Pro tier',
            description: 'Proposal to increase Pro tier API calls from 100 to 250 per day',
            votes_for: 45000,
            votes_against: 12000,
            status: 'active',
            ends_at: '2026-02-15'
          },
          {
            id: '2',
            title: 'Add new VIP benefits',
            description: 'Add priority support and custom integrations for VIP tier',
            votes_for: 78000,
            votes_against: 5000,
            status: 'active',
            ends_at: '2026-02-10'
          }
        ]);
      } else {
        setProposals(data || []);
      }
      setLoading(false);
    }

    fetchProposals();
  }, []);

  // Cast vote (demo mode - no wallet required)
  const castVote = async (proposalId: string, voteFor: boolean) => {
    setVoting(proposalId);

    try {
      // Demo mode - just update local state
      alert('Vote recorded (demo mode)');

      // Update local state
      setProposals(prev => prev.map(p => {
        if (p.id === proposalId) {
          return {
            ...p,
            votes_for: voteFor ? p.votes_for + 1 : p.votes_for,
            votes_against: !voteFor ? p.votes_against + 1 : p.votes_against
          };
        }
        return p;
      }));
    } catch (err) {
      console.error('Vote error:', err);
    }

    setVoting(null);
  };

  const votePercentage = (forVotes: number, againstVotes: number) => {
    const total = forVotes + againstVotes;
    return total > 0 ? Math.round((forVotes / total) * 100) : 0;
  };

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Live Status Banner */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white text-center py-2 px-4 text-sm">
        <span className="font-semibold">🟢 Live</span> — Vote on proposals. <a href="/docs" className="underline">Learn more</a>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">
            <span className="text-red-500">Governance</span> Portal
          </h1>
          <div className="flex items-center gap-4">
            <a href="/" className="text-gray-400 hover:text-white">← Back</a>
          </div>
        </div>

        {/* Active Proposals */}
        <h2 className="text-xl font-semibold mb-4">Active Proposals</h2>
        
        {loading ? (
          <p className="text-gray-400">Loading proposals...</p>
        ) : proposals.length === 0 ? (
          <p className="text-gray-400">No active proposals</p>
        ) : (
          <div className="space-y-4">
            {proposals.map((proposal) => (
              <div key={proposal.id} className="bg-gray-900 p-6 rounded-lg border border-gray-800">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">{proposal.title}</h3>
                    <p className="text-gray-400 text-sm mt-1">{proposal.description}</p>
                  </div>
                  <span className="bg-green-600 text-xs px-2 py-1 rounded">
                    {proposal.status.toUpperCase()}
                  </span>
                </div>
                
                {/* Vote Progress */}
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-green-400">For: {proposal.votes_for.toLocaleString()}</span>
                    <span className="text-red-400">Against: {proposal.votes_against.toLocaleString()}</span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-green-500"
                      style={{ width: `${votePercentage(proposal.votes_for, proposal.votes_against)}%` }}
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <p className="text-gray-400 text-sm">Ends: {proposal.ends_at}</p>
                  <div className="space-x-2">
                    <button 
                      onClick={() => castVote(proposal.id, true)}
                      disabled={voting === proposal.id}
                      className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-4 py-2 rounded text-sm"
                    >
                      {voting === proposal.id ? '...' : 'Vote For'}
                    </button>
                    <button 
                      onClick={() => castVote(proposal.id, false)}
                      disabled={voting === proposal.id}
                      className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-4 py-2 rounded text-sm"
                    >
                      {voting === proposal.id ? '...' : 'Vote Against'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}