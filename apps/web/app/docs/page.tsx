'use client';

import { useState } from 'react';

export default function DocsPage() {
  const [testAction, setTestAction] = useState('delete');
  const [testTarget, setTestTarget] = useState('production_database');
  const [testResult, setTestResult] = useState<{
    allowed: boolean;
    blocked: boolean;
    action: string;
    target: string;
    risk_score: number;
    reasons: string[];
    kill_latency_ms: number;
    timestamp: string;
    audit_log_id: string;
  } | null>(null);
  const [testing, setTesting] = useState(false);

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 800));
    
    setTestResult({
      allowed: false,
      blocked: true,
      action: testAction,
      target: testTarget,
      risk_score: 95,
      reasons: [
        `Action '${testAction}' is blocked by security policy`,
        `Target '${testTarget}' is on protected list`,
        "High-risk operation requires manual approval"
      ],
      kill_latency_ms: 73,
      timestamp: new Date().toISOString(),
      audit_log_id: `audit_${Date.now()}`
    });
    
    setTesting(false);
  };

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">
            <span className="text-red-500">$KILLSWITCH</span> Integration Guide
          </h1>
          <a href="/" className="text-gray-400 hover:text-white">← Home</a>
        </div>

        {/* Live Test Demo */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">Try It Live (No Signup)</h2>
          <div className="bg-gradient-to-br from-red-950/30 to-purple-950/20 rounded-lg border border-red-500/30 p-6">
            <p className="text-gray-300 mb-6">Test the kill switch with a simulated dangerous action:</p>
            
            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Action</label>
                <select 
                  value={testAction}
                  onChange={(e) => setTestAction(e.target.value)}
                  className="w-full bg-black border border-gray-700 rounded px-4 py-2 text-white"
                >
                  <option value="delete">delete</option>
                  <option value="exec">exec</option>
                  <option value="sudo">sudo</option>
                  <option value="transfer">transfer</option>
                  <option value="exfiltrate">exfiltrate</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Target</label>
                <input
                  type="text"
                  value={testTarget}
                  onChange={(e) => setTestTarget(e.target.value)}
                  className="w-full bg-black border border-gray-700 rounded px-4 py-2 text-white"
                  placeholder="e.g., production_database"
                />
              </div>
            </div>

            <button
              onClick={runTest}
              disabled={testing}
              className="bg-red-600 hover:bg-red-500 disabled:bg-gray-600 text-white font-semibold px-8 py-3 rounded-lg transition w-full md:w-auto"
            >
              {testing ? 'Testing...' : '🚨 Test Kill Switch'}
            </button>

            {testResult && (
              <div className="mt-6">
                <p className="text-sm text-gray-400 mb-2">Response:</p>
                <pre className="bg-black border border-gray-700 rounded p-4 overflow-x-auto text-sm">
                  <code className="text-green-400">{JSON.stringify(testResult, null, 2)}</code>
                </pre>
                <div className="mt-4 flex items-center gap-2 text-sm">
                  <span className="text-red-500 font-semibold">✗ BLOCKED</span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400">Terminated in {testResult.kill_latency_ms}ms</span>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Quick Start */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">Quick Start</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <p className="text-gray-300 mb-4">Install the SDK in your AI agent project:</p>
            <pre className="bg-black rounded p-4 overflow-x-auto">
              <code className="text-green-400">pip install killswitch-fence</code>
            </pre>
          </div>
        </section>

        {/* Python Integration */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">Python Integration</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <p className="text-gray-300 mb-4">Wrap your AI agent with the killswitch fence:</p>
            <pre className="bg-black rounded p-4 overflow-x-auto text-sm">
              <code className="text-gray-300">{`from killswitch import RuntimeFence

# Initialize the fence with your API key
fence = RuntimeFence(
    api_key="your_api_key",
    agent_id="your_agent_id"
)

# Wrap your agent's main function
@fence.guard
async def my_agent_action(prompt: str):
    # Your AI logic here
    response = await ai.generate(prompt)
    return response

# The fence automatically:
# - Checks if agent is allowed to run
# - Logs all actions for audit
# - Enforces rate limits
# - Can be killed remotely via dashboard`}</code>
            </pre>
          </div>
        </section>

        {/* TypeScript Integration */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">TypeScript/JavaScript Integration</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <p className="text-gray-300 mb-4">Install via npm:</p>
            <pre className="bg-black rounded p-4 mb-4">
              <code className="text-green-400">npm install @killswitch/sdk</code>
            </pre>
            <p className="text-gray-300 mb-4">Usage:</p>
            <pre className="bg-black rounded p-4 overflow-x-auto text-sm">
              <code className="text-gray-300">{`import { KillswitchClient } from '@killswitch/sdk';

const client = new KillswitchClient({
  apiKey: process.env.KILLSWITCH_API_KEY,
  agentId: 'your-agent-id'
});

// Check if agent is allowed to run
const canRun = await client.checkStatus();

if (canRun) {
  // Execute your agent logic
  await runAgentTask();
  
  // Log the action
  await client.logAction('task_completed', { result: 'success' });
}`}</code>
            </pre>
          </div>
        </section>

        {/* API Reference */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">API Reference</h2>
          <div className="space-y-4">
            {/* Check Status */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="bg-green-600 text-xs px-2 py-1 rounded font-mono">GET</span>
                <code className="text-white">/api/v1/agent/status</code>
              </div>
              <p className="text-gray-400 text-sm mb-4">Check if an agent is allowed to run</p>
              <p className="text-gray-300 text-sm">Returns: <code className="text-green-400">{`{ status: 'active' | 'paused' | 'killed' }`}</code></p>
            </div>

            {/* Log Action */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="bg-blue-600 text-xs px-2 py-1 rounded font-mono">POST</span>
                <code className="text-white">/api/v1/agent/log</code>
              </div>
              <p className="text-gray-400 text-sm mb-4">Log an action for audit trail</p>
              <p className="text-gray-300 text-sm">Body: <code className="text-green-400">{`{ action: string, metadata: object }`}</code></p>
            </div>

            {/* Kill Agent */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="bg-red-600 text-xs px-2 py-1 rounded font-mono">POST</span>
                <code className="text-white">/api/v1/agent/kill</code>
              </div>
              <p className="text-gray-400 text-sm mb-4">Immediately terminate an agent</p>
              <p className="text-gray-300 text-sm">Body: <code className="text-green-400">{`{ agent_id: string, reason?: string }`}</code></p>
            </div>
          </div>
        </section>

        {/* Dashboard Access */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">Dashboard</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <p className="text-gray-300 mb-4">
              Access the dashboard to monitor and control your agents in real-time:
            </p>
            <ul className="list-disc list-inside text-gray-400 space-y-2 mb-4">
              <li>View all registered agents and their status</li>
              <li>Pause or kill agents instantly</li>
              <li>Monitor API usage and rate limits</li>
              <li>View audit logs and action history</li>
              <li>Set up alerts and notifications</li>
            </ul>
            <a 
              href="/agents" 
              className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-6 rounded inline-block"
            >
              Open Dashboard →
            </a>
          </div>
        </section>

        {/* Token Benefits */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4 text-red-400">Token Holder Benefits</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <p className="text-gray-300 mb-4">Hold $KILLSWITCH tokens to unlock discounts:</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div className="bg-black rounded p-4">
                <p className="text-2xl font-bold text-white">10K</p>
                <p className="text-gray-400 text-sm">tokens</p>
                <p className="text-green-400 font-semibold">10% off</p>
              </div>
              <div className="bg-black rounded p-4">
                <p className="text-2xl font-bold text-white">100K</p>
                <p className="text-gray-400 text-sm">tokens</p>
                <p className="text-green-400 font-semibold">20% off</p>
              </div>
              <div className="bg-black rounded p-4">
                <p className="text-2xl font-bold text-white">1M</p>
                <p className="text-gray-400 text-sm">tokens</p>
                <p className="text-green-400 font-semibold">40% off</p>
              </div>
              <div className="bg-black rounded p-4">
                <p className="text-2xl font-bold text-white">1M+</p>
                <p className="text-gray-400 text-sm">tokens</p>
                <p className="text-green-400 font-semibold">2x votes</p>
              </div>
            </div>
            <div className="mt-4 text-center">
              <a 
                href="https://jup.ag/tokens/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon"
                target="_blank"
                rel="noopener noreferrer"
                className="text-purple-400 hover:text-purple-300"
              >
                Buy $KILLSWITCH on Jupiter →
              </a>
            </div>
          </div>
        </section>

        {/* Support */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-red-400">Support</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <a 
                href="https://github.com/RunTimeAdmin/ai-agent-killswitch"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-black hover:bg-gray-800 rounded p-4 text-center transition"
              >
                <svg className="w-8 h-8 mx-auto mb-2" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                <p className="text-white font-semibold">GitHub</p>
                <p className="text-gray-400 text-sm">Source code</p>
              </a>
              <a 
                href="https://x.com/protocol14019"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-black hover:bg-gray-800 rounded p-4 text-center transition"
              >
                <svg className="w-8 h-8 mx-auto mb-2" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                <p className="text-white font-semibold">Twitter</p>
                <p className="text-gray-400 text-sm">@protocol14019</p>
              </a>
              <a 
                href="mailto:help@protocol14019.com"
                className="bg-black hover:bg-gray-800 rounded p-4 text-center transition"
              >
                <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <p className="text-white font-semibold">Email</p>
                <p className="text-gray-400 text-sm">Get help</p>
              </a>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
