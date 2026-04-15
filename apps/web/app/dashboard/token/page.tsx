'use client';
import { useState } from 'react';
import Link from 'next/link';

interface TokenData {
  balance: number;
  staked: number;
  governancePower: number;
  rewards: number;
}

export default function TokenPage() {
  const [connected, setConnected] = useState(false);
  const [wallet, setWallet] = useState('');
  const [tokenData, setTokenData] = useState<TokenData>({
    balance: 0,
    staked: 0,
    governancePower: 0,
    rewards: 0
  });
  const [stakeAmount, setStakeAmount] = useState('');

  const connectWallet = async () => {
    // Phantom wallet connection
    if (typeof window !== 'undefined' && (window as any).solana?.isPhantom) {
      try {
        const resp = await (window as any).solana.connect();
        setWallet(resp.publicKey.toString());
        setConnected(true);
        // Fetch token balance from API
        fetchTokenData(resp.publicKey.toString());
      } catch (err) {
        console.error('Wallet connection failed:', err);
      }
    } else {
      alert('Please install Phantom wallet');
    }
  };

  const fetchTokenData = async (walletAddress: string) => {
    try {
      const res = await fetch(`/api/token/holdings?wallet=${walletAddress}`);
      const data = await res.json();
      setTokenData({
        balance: data.balance || 0,
        staked: data.staked || 0,
        governancePower: data.governancePower || 0,
        rewards: 0
      });
    } catch (err) {
      console.error('Failed to fetch token data:', err);
    }
  };

  const handleStake = async () => {
    if (!stakeAmount || parseFloat(stakeAmount) <= 0) return;
    // TODO: Implement staking transaction
    alert(`Staking ${stakeAmount} $KILLSWITCH - Transaction pending`);
    setStakeAmount('');
  };

  const handleUnstake = async () => {
    // TODO: Implement unstaking transaction
    alert('Unstaking - Transaction pending');
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white">
      <nav className="flex justify-between items-center p-6 border-b border-gray-800">
        <Link href="/" className="text-2xl font-bold text-red-500">KILLSWITCH</Link>
        <div className="flex gap-4">
          <Link href="/dashboard" className="text-gray-400 hover:text-white">Dashboard</Link>
          <Link href="/dashboard/token" className="text-white">Token</Link>
          <Link href="/dashboard/runtime" className="text-gray-400 hover:text-white">Runtime</Link>
          <Link href="/governance" className="text-gray-400 hover:text-white">Governance</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-8">$KILLSWITCH Token</h1>

        {!connected ? (
          <div className="bg-gray-800 rounded-xl p-8 text-center">
            <h2 className="text-xl mb-4">Connect Your Wallet</h2>
            <p className="text-gray-400 mb-6">Connect your Solana wallet to view your $KILLSWITCH holdings</p>
            <button onClick={connectWallet} className="bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg font-semibold">
              Connect Phantom
            </button>
          </div>
        ) : (
          <>
            <div className="bg-gray-800 rounded-xl p-6 mb-6">
              <div className="text-gray-400 text-sm mb-2">Connected Wallet</div>
              <div className="font-mono text-sm">{wallet}</div>
            </div>

            <div className="grid md:grid-cols-4 gap-6 mb-8">
              <div className="bg-gray-800 p-6 rounded-xl">
                <div className="text-gray-400 text-sm">Balance</div>
                <div className="text-2xl font-bold">{tokenData.balance.toLocaleString()}</div>
                <div className="text-gray-500 text-sm">$KILLSWITCH</div>
              </div>
              <div className="bg-gray-800 p-6 rounded-xl">
                <div className="text-gray-400 text-sm">Staked</div>
                <div className="text-2xl font-bold text-purple-500">{tokenData.staked.toLocaleString()}</div>
                <div className="text-gray-500 text-sm">$KILLSWITCH</div>
              </div>
              <div className="bg-gray-800 p-6 rounded-xl">
                <div className="text-gray-400 text-sm">Governance Power</div>
                <div className="text-2xl font-bold text-blue-500">{tokenData.governancePower}</div>
                <div className="text-gray-500 text-sm">Votes</div>
              </div>
              <div className="bg-gray-800 p-6 rounded-xl">
                <div className="text-gray-400 text-sm">Rewards</div>
                <div className="text-2xl font-bold text-green-500">{tokenData.rewards}</div>
                <div className="text-gray-500 text-sm">Claimable</div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-bold mb-4">Stake Tokens</h3>
                <p className="text-gray-400 text-sm mb-4">Stake $KILLSWITCH to earn governance power and priority audit access</p>
                <div className="flex gap-2 mb-4">
                  <input
                    type="number"
                    value={stakeAmount}
                    onChange={(e) => setStakeAmount(e.target.value)}
                    placeholder="Amount to stake"
                    className="flex-1 bg-gray-700 rounded px-4 py-2"
                  />
                  <button onClick={handleStake} className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded">
                    Stake
                  </button>
                </div>
                <button onClick={() => setStakeAmount(tokenData.balance.toString())} className="text-purple-400 text-sm">
                  Max: {tokenData.balance.toLocaleString()}
                </button>
              </div>

              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-bold mb-4">Unstake Tokens</h3>
                <p className="text-gray-400 text-sm mb-4">Unstaking has a 7-day cooldown period</p>
                <div className="text-2xl font-bold mb-4">{tokenData.staked.toLocaleString()} <span className="text-gray-400 text-sm">staked</span></div>
                <button onClick={handleUnstake} disabled={tokenData.staked === 0} className="bg-gray-600 hover:bg-gray-500 disabled:opacity-50 px-6 py-2 rounded w-full">
                  Unstake All
                </button>
              </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-6 mt-6">
              <h3 className="text-lg font-bold mb-4">Token Utilities</h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-gray-700 p-4 rounded-lg">
                  <div className="text-purple-400 font-semibold mb-2">Governance</div>
                  <div className="text-gray-400 text-sm">Vote on protocol proposals</div>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <div className="text-blue-400 font-semibold mb-2">Priority Access</div>
                  <div className="text-gray-400 text-sm">Skip audit queue with staked tokens</div>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <div className="text-green-400 font-semibold mb-2">Fee Discounts</div>
                  <div className="text-gray-400 text-sm">Reduced fees for token holders</div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
