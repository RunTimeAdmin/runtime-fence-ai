import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white">
      <nav className="flex justify-between items-center p-6 max-w-7xl mx-auto">
        <div className="text-2xl font-bold text-red-500">KILLSWITCH</div>
        <div className="flex gap-6">
          <Link href="/dashboard" className="hover:text-red-400">Dashboard</Link>
          <Link href="/tools" className="hover:text-red-400">Tools</Link>
          <Link href="/governance" className="hover:text-red-400">Governance</Link>
          <Link href="/learn" className="hover:text-red-400">Learn</Link>
          <button className="bg-red-600 px-4 py-2 rounded-lg hover:bg-red-700">Connect Wallet</button>
        </div>
      </nav>

      <section className="max-w-7xl mx-auto px-6 py-20 text-center">
        <h1 className="text-6xl font-bold mb-6">
          AI Agent <span className="text-red-500">Safety</span> Infrastructure
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-3xl mx-auto">
          The complete kill switch ecosystem for AI agents. Monitor, control, and protect 
          your autonomous systems with enterprise-grade safety controls.
        </p>
        <div className="flex gap-4 justify-center">
          <button className="bg-red-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-red-700">
            Get Started
          </button>
          <button className="border border-gray-600 px-8 py-4 rounded-lg text-lg hover:border-red-500">
            View Documentation
          </button>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-8">
          <div className="bg-gray-800 p-8 rounded-xl">
            <div className="text-red-500 text-4xl mb-4">01</div>
            <h3 className="text-xl font-bold mb-2">Kill Switch Core</h3>
            <p className="text-gray-400">Instant termination controls for AI agents with circuit breakers and behavioral analysis.</p>
          </div>
          <div className="bg-gray-800 p-8 rounded-xl">
            <div className="text-red-500 text-4xl mb-4">02</div>
            <h3 className="text-xl font-bold mb-2">Real-time Monitoring</h3>
            <p className="text-gray-400">eBPF-powered network monitoring and anomaly detection for agent activities.</p>
          </div>
          <div className="bg-gray-800 p-8 rounded-xl">
            <div className="text-red-500 text-4xl mb-4">03</div>
            <h3 className="text-xl font-bold mb-2">Decentralized Governance</h3>
            <p className="text-gray-400">Community-driven safety policies with token-holder voting and proposals.</p>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 py-16 text-center">
        <h2 className="text-4xl font-bold mb-4">Token Integration</h2>
        <p className="text-gray-400 mb-8">Hold KILLSWITCH tokens for governance voting, premium features, and staking rewards.</p>
        <div className="flex gap-6 justify-center flex-wrap">
          <div className="bg-gray-800 px-6 py-4 rounded-lg"><span className="text-red-500">Governance</span> Voting</div>
          <div className="bg-gray-800 px-6 py-4 rounded-lg"><span className="text-red-500">Premium</span> Features</div>
          <div className="bg-gray-800 px-6 py-4 rounded-lg"><span className="text-red-500">Staking</span> Rewards</div>
          <div className="bg-gray-800 px-6 py-4 rounded-lg"><span className="text-red-500">API</span> Rate Boost</div>
        </div>
      </section>

      <footer className="border-t border-gray-800 mt-20 py-10 text-center text-gray-500">
        <p>KILLSWITCH Protocol - AI Agent Safety Infrastructure</p>
      </footer>
    </main>
  );
}
