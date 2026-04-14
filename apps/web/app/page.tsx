export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white">
      {/* Live Status Banner */}
      <div className="fixed top-0 w-full z-[60] bg-gradient-to-r from-green-600 to-emerald-600 text-white text-center py-2 px-4">
        <span className="font-semibold">🟢 Live & Operational</span>
        <span className="mx-2">—</span>
        <span>API is live. Token is live on Solana. <a href="/docs" className="underline font-semibold hover:no-underline">Test it now →</a></span>
      </div>

      {/* Navigation */}
      <nav className="fixed top-10 w-full z-50 bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight">KILLSWITCH</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="/agents" className="text-sm text-gray-400 hover:text-white transition">Dashboard</a>
            <a href="/subscription" className="text-sm text-gray-400 hover:text-white transition">Pricing</a>
            <a href="/governance" className="text-sm text-gray-400 hover:text-white transition">Governance</a>
            <a href="/docs" className="text-sm text-gray-400 hover:text-white transition">Docs</a>
            <a href="https://github.com/RunTimeAdmin/ai-agent-killswitch" target="_blank" className="text-sm text-gray-400 hover:text-white transition">GitHub</a>
            <a href="/agents" className="bg-red-600 hover:bg-red-500 text-sm font-medium px-4 py-2 rounded-lg transition">Get Started</a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-20 overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600/20 rounded-full blur-[128px]" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-[128px]" />
        </div>
        <div className="relative max-w-7xl mx-auto px-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-full px-4 py-1.5 mb-8">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm text-green-300">Live on Solana — API Operational</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
              The kill switch<br />
              <span className="text-red-500">AI agents need.</span>
            </h1>
            <p className="text-xl text-gray-400 mb-10 max-w-xl">
              Enterprise-grade safety infrastructure for autonomous AI. 
              Real-time monitoring, instant termination, and cryptographic identity—all in under 100ms.
            </p>
            <div className="flex flex-wrap gap-4">
              <a href="/docs" className="bg-red-600 hover:bg-red-500 font-semibold px-8 py-4 rounded-xl transition inline-flex items-center gap-2">
                Test It Now (No Signup)
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
              </a>
              <a href="https://github.com/RunTimeAdmin/ai-agent-killswitch" target="_blank" className="bg-white/5 hover:bg-white/10 border border-white/10 font-semibold px-8 py-4 rounded-xl transition inline-flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" /></svg>
                View on GitHub
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Live Stats Bar */}
      <section className="border-y border-white/5 bg-white/[0.02]">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
            <div className="text-center">
              <a href="https://github.com/RunTimeAdmin/ai-agent-killswitch/actions" target="_blank" rel="noopener noreferrer" className="group block">
                <p className="text-3xl font-bold text-white group-hover:text-green-400 transition">82/82</p>
                <p className="text-sm text-gray-500 mt-1 group-hover:text-gray-400 transition">Tests Passing</p>
              </a>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-white">&lt;100<span className="text-lg">ms</span></p>
              <p className="text-sm text-gray-500 mt-1">Kill Latency</p>
            </div>
            <div className="text-center">
              <a href="https://status.killswitch.protocol14019.com" target="_blank" rel="noopener noreferrer" className="group block">
                <p className="text-3xl font-bold text-white group-hover:text-green-400 transition">99.9<span className="text-lg">%</span></p>
                <p className="text-sm text-gray-500 mt-1 group-hover:text-gray-400 transition">API Uptime</p>
              </a>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-white">6</p>
              <p className="text-sm text-gray-500 mt-1">Security Modules</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-white">Live</p>
              <p className="text-sm text-gray-500 mt-1">On Solana</p>
            </div>
          </div>
        </div>
      </section>

      {/* Code Preview */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold mb-4">One decorator.<br />Complete protection.</h2>
              <p className="text-gray-400 mb-6">
                Add enterprise-grade safety to any AI agent with a single line of code. 
                Works with OpenAI, Anthropic, LangChain, and any custom implementation.
              </p>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <span className="text-gray-300">Real-time behavioral monitoring</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <span className="text-gray-300">Automatic SPIFFE identity binding</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-3.5 h-3.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <span className="text-gray-300">Sub-100ms emergency termination</span>
                </div>
              </div>
            </div>
            <div className="bg-[#111] rounded-2xl border border-white/10 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 bg-white/5 border-b border-white/5">
                <div className="flex gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-500/80" />
                  <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <span className="w-3 h-3 rounded-full bg-green-500/80" />
                </div>
                <span className="text-xs text-gray-500 ml-2">agent.py</span>
              </div>
              <pre className="p-6 text-sm overflow-x-auto">
                <code>
                  <span className="text-gray-500"># Your agent running live trades</span>{"\n"}
                  <span className="text-yellow-400">@fence.protect</span>(agent_id=<span className="text-green-400">&quot;trading-bot-001&quot;</span>){"\n"}
                  <span className="text-purple-400">def</span> <span className="text-blue-400">trading_bot</span>():{"\n"}
                  {"    "}<span className="text-purple-400">while</span> <span className="text-blue-400">True</span>:{"\n"}
                  {"        "}execute_trades(){"\n"}
                  {"\n"}
                  <span className="text-gray-500"># Click KILL in dashboard → Agent stops in &lt;100ms</span>{"\n"}
                  <span className="text-gray-500"># Result: SIGTERM → SIGKILL escalation</span>{"\n"}
                  <span className="text-gray-500"># Audit log: &quot;Terminated by wallet 0x...&quot;</span>{"\n"}
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 bg-gradient-to-b from-transparent via-red-950/5 to-transparent">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">Defense in depth</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">6 security modules working together to ensure your AI agents stay within bounds</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z", title: "Runtime Fence", desc: "Monitor every action in real-time with configurable boundaries and instant alerts" },
              { icon: "M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636", title: "Instant Kill Switch", desc: "One-click termination with SIGTERM → SIGKILL escalation for rogue agents" },
              { icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2", title: "Audit Logging", desc: "Complete audit trail with cryptographic verification for compliance" },
              { icon: "M13 10V3L4 14h7v7l9-11h-7z", title: "Sub-Second Response", desc: "Kill signals processed in under 100ms when safety matters most" },
              { icon: "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z", title: "SPIFFE Identity", desc: "Cryptographic workload identity with automatic certificate rotation" },
              { icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z", title: "Token Governance", desc: "Decentralized oversight with $KILLSWITCH token voting rights" },
            ].map((f, i) => (
              <div key={i} className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 hover:border-red-500/30 transition">
                <div className="w-12 h-12 bg-red-500/10 rounded-xl flex items-center justify-center mb-4">
                  <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={f.icon} />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Token Section */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="bg-gradient-to-br from-red-950/30 to-purple-950/20 rounded-3xl border border-white/10 overflow-hidden">
            <div className="grid md:grid-cols-2">
              <div className="p-12">
                <span className="text-red-500 font-semibold text-sm">$KILLSWITCH TOKEN</span>
                <h2 className="text-3xl font-bold mt-2 mb-4">Stake in AI safety</h2>
                <p className="text-gray-400 mb-8">
                  Token holders govern protocol upgrades, earn subscription discounts, 
                  and participate in the decentralized oversight network.
                </p>
                <div className="space-y-3 mb-8">
                  {[
                    '1K+ tokens → Vote on proposals',
                    '10K+ tokens → 10% subscription discount',
                    '100K+ tokens → 20% discount + Oracle eligibility',
                    '1M+ tokens → 40% discount + 2× voting power',
                  ].map((b, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                      <span className="text-gray-300 text-sm">{b}</span>
                    </div>
                  ))}
                </div>
                <a href="https://jup.ag/tokens/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-500 font-semibold px-6 py-3 rounded-xl transition">
                  Buy on Jupiter
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              </div>
              <div className="bg-black/30 p-12 flex flex-col items-center justify-center">
                <div className="text-center">
                  <p className="text-gray-500 text-sm mb-3">Contract Address</p>
                  <div className="bg-black/50 border border-white/10 rounded-xl px-6 py-4 mb-4">
                    <code className="text-red-400 text-sm font-mono break-all">56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon</code>
                  </div>
                  <p className="text-gray-500 text-xs mb-3">Solana • SPL Token</p>
                  <div className="flex flex-col gap-2 w-full max-w-xs">
                    <a href="https://solscan.io/token/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon" target="_blank" rel="noopener noreferrer" className="text-xs text-purple-400 hover:text-purple-300 underline">View on Solscan →</a>
                    <a href="https://birdeye.so/token/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon" target="_blank" rel="noopener noreferrer" className="text-xs text-purple-400 hover:text-purple-300 underline">View on Birdeye →</a>
                    <a href="https://jup.ag/tokens/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon" target="_blank" rel="noopener noreferrer" className="text-xs text-purple-400 hover:text-purple-300 underline">Trade on Jupiter →</a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 bg-gradient-to-b from-transparent via-red-950/5 to-transparent">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <h2 className="text-4xl font-bold mb-4">Ready to secure your AI agents?</h2>
          <p className="text-gray-400 mb-4 max-w-xl mx-auto">
            Get started in minutes. Test the API live - no signup required.
          </p>
          <p className="text-sm text-gray-500 mb-10 max-w-xl mx-auto">
            <strong className="text-white">Free tier:</strong> 100 API calls/day, 1 agent monitored<br />
            <strong className="text-white">Token holders:</strong> Unlimited calls, unlimited agents, governance votes
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <a href="/docs" className="bg-red-600 hover:bg-red-500 font-semibold px-8 py-4 rounded-xl transition">Test the API Now</a>
            <a href="/subscription" className="bg-white/5 hover:bg-white/10 border border-white/10 font-semibold px-8 py-4 rounded-xl transition">View Pricing</a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-red-600 rounded flex items-center justify-center">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>
              </div>
              <span className="text-sm text-gray-400">© 2026 KILLSWITCH</span>
            </div>
            <div className="flex items-center gap-8">
              <a href="https://github.com/RunTimeAdmin/ai-agent-killswitch" target="_blank" className="text-sm text-gray-500 hover:text-white transition">GitHub</a>
              <a href="/governance" className="text-sm text-gray-500 hover:text-white transition">Governance</a>
              <a href="/subscription" className="text-sm text-gray-500 hover:text-white transition">Pricing</a>
              <a href="/agents" className="text-sm text-gray-500 hover:text-white transition">Dashboard</a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}