'use client';

import { useState, useEffect, useRef } from 'react';

interface ActivityEvent {
  type: string;
  agent_id: string;
  action: string;
  target: string;
  risk_score: number;
  risk_level: string;
  allowed: boolean;
  timestamp: number;
}

function getRiskColor(level: string): string {
  switch (level?.toUpperCase()) {
    case 'LOW': return 'text-green-400';
    case 'MEDIUM': return 'text-yellow-400';
    case 'HIGH': return 'text-orange-500';
    case 'CRITICAL': return 'text-red-500';
    default: return 'text-gray-400';
  }
}

function getRiskBg(level: string): string {
  switch (level?.toUpperCase()) {
    case 'LOW': return 'bg-green-500/10 border-green-500/20';
    case 'MEDIUM': return 'bg-yellow-500/10 border-yellow-500/20';
    case 'HIGH': return 'bg-orange-500/10 border-orange-500/20';
    case 'CRITICAL': return 'bg-red-500/10 border-red-500/20';
    default: return 'bg-gray-500/10 border-gray-500/20';
  }
}

export default function LiveDashboard() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState({ total: 0, blocked: 0, avgRisk: 0 });
  const wsRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3001';
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'dashboard' }));
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'activity' || data.type === 'kill') {
          setEvents(prev => {
            const updated = [data, ...prev].slice(0, 100); // Keep last 100
            return updated;
          });
          setStats(prev => ({
            total: prev.total + 1,
            blocked: prev.blocked + (data.allowed === false ? 1 : 0),
            avgRisk: Math.round(
              ((prev.avgRisk * prev.total) + (data.risk_score || 0)) / (prev.total + 1)
            ),
          }));
        }
      } catch (e) {}
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    return () => ws.close();
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [events]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Runtime Fence — Live Activity</h1>
          <p className="text-gray-400 mt-1">Real-time agent monitoring dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-400">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <p className="text-gray-400 text-sm">Total Events</p>
          <p className="text-2xl font-bold">{stats.total}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <p className="text-gray-400 text-sm">Blocked</p>
          <p className="text-2xl font-bold text-red-400">{stats.blocked}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <p className="text-gray-400 text-sm">Allowed</p>
          <p className="text-2xl font-bold text-green-400">{stats.total - stats.blocked}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <p className="text-gray-400 text-sm">Avg Risk Score</p>
          <p className="text-2xl font-bold">{stats.avgRisk}</p>
        </div>
      </div>

      {/* Live Feed */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="font-semibold">Live Event Feed</h2>
          <span className="text-xs text-gray-500">{events.length} events</span>
        </div>
        <div ref={feedRef} className="max-h-[600px] overflow-y-auto">
          {events.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <p className="text-lg">Waiting for agent activity...</p>
              <p className="text-sm mt-2">Run a demo script to see events appear here in real-time</p>
            </div>
          ) : (
            events.map((event, i) => (
              <div
                key={`${event.timestamp}-${i}`}
                className={`px-6 py-3 border-b border-gray-800/50 flex items-center gap-4 hover:bg-gray-800/30 transition-colors ${i === 0 ? 'animate-pulse-once' : ''}`}
              >
                {/* Status indicator */}
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${event.allowed ? 'bg-green-500' : 'bg-red-500'}`} />
                
                {/* Timestamp */}
                <span className="text-xs text-gray-500 font-mono w-20 flex-shrink-0">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                
                {/* Agent */}
                <span className="text-sm font-medium text-cyan-400 w-32 truncate flex-shrink-0">
                  {event.agent_id}
                </span>
                
                {/* Action */}
                <span className="text-sm text-gray-300 w-40 truncate flex-shrink-0">
                  {event.action}
                </span>
                
                {/* Target */}
                <span className="text-sm text-gray-500 flex-1 truncate">
                  {event.target}
                </span>
                
                {/* Risk badge */}
                <span className={`text-xs px-2 py-1 rounded border flex-shrink-0 ${getRiskBg(event.risk_level)}`}>
                  <span className={getRiskColor(event.risk_level)}>
                    {event.risk_level} ({event.risk_score})
                  </span>
                </span>
                
                {/* Status */}
                <span className={`text-xs font-bold flex-shrink-0 w-16 text-right ${event.allowed ? 'text-green-400' : 'text-red-400'}`}>
                  {event.type === 'kill' ? '🚨 KILL' : event.allowed ? '✓ PASS' : '✗ BLOCK'}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
