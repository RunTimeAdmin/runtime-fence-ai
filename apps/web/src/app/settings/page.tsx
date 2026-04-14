'use client';

import { useState, useEffect } from 'react';

interface AgentPreset {
  id: string;
  name: string;
  description: string;
  blockedActions: string[];
  blockedTargets: string[];
  spendingLimit: number;
  riskThreshold: 'low' | 'medium' | 'high';
}

const AGENT_PRESETS: AgentPreset[] = [
  {
    id: 'coding',
    name: 'Coding Assistant',
    description: 'For AI coding tools like Copilot, Cursor, Aider',
    blockedActions: ['exec', 'shell', 'rm', 'sudo', 'install', 'push', 'deploy'],
    blockedTargets: ['.env', '.ssh', 'node_modules', '/etc', 'credentials', 'password'],
    spendingLimit: 0,
    riskThreshold: 'medium'
  },
  {
    id: 'email',
    name: 'Email Bot',
    description: 'For email automation agents',
    blockedActions: ['send_bulk', 'forward_all', 'delete_all', 'export', 'share_external'],
    blockedTargets: ['all_contacts', 'external', 'spam', 'admin@'],
    spendingLimit: 100,
    riskThreshold: 'medium'
  },
  {
    id: 'data',
    name: 'Data Analyst',
    description: 'For data processing agents',
    blockedActions: ['delete', 'drop_table', 'truncate', 'export_pii', 'share', 'modify_schema'],
    blockedTargets: ['production', 'pii_table', 'financial', 'passwords', 'audit_log'],
    spendingLimit: 1000000,
    riskThreshold: 'high'
  },
  {
    id: 'web',
    name: 'Web Browser',
    description: 'For web scraping and browsing agents',
    blockedActions: ['submit_form', 'login', 'purchase', 'download_exe', 'click_ad', 'post'],
    blockedTargets: ['banking', 'payment', 'admin', '.exe', 'darkweb', 'malware'],
    spendingLimit: 0,
    riskThreshold: 'medium'
  },
  {
    id: 'autonomous',
    name: 'Autonomous Agent',
    description: 'For AutoGPT, BabyAGI, CrewAI style agents',
    blockedActions: ['spawn_agent', 'modify_self', 'access_internet', 'execute_code', 'create_file', 'send_request', 'purchase', 'sign_contract'],
    blockedTargets: ['api_keys', 'wallets', 'bank', 'social_media', 'email', 'production'],
    spendingLimit: 10,
    riskThreshold: 'low'
  },
  {
    id: 'custom',
    name: 'Custom',
    description: 'Create your own rules',
    blockedActions: [],
    blockedTargets: [],
    spendingLimit: 100,
    riskThreshold: 'medium'
  }
];

export default function SettingsPage() {
  const [selectedPreset, setSelectedPreset] = useState<string>('coding');
  const [blockedActions, setBlockedActions] = useState<string[]>([]);
  const [blockedTargets, setBlockedTargets] = useState<string[]>([]);
  const [spendingLimit, setSpendingLimit] = useState<number>(0);
  const [riskThreshold, setRiskThreshold] = useState<'low' | 'medium' | 'high'>('medium');
  const [newAction, setNewAction] = useState('');
  const [newTarget, setNewTarget] = useState('');
  const [saved, setSaved] = useState(false);
  const [autoKill, setAutoKill] = useState(true);
  const [offlineMode, setOfflineMode] = useState(false);

  useEffect(() => {
    const preset = AGENT_PRESETS.find(p => p.id === selectedPreset);
    if (preset) {
      setBlockedActions([...preset.blockedActions]);
      setBlockedTargets([...preset.blockedTargets]);
      setSpendingLimit(preset.spendingLimit);
      setRiskThreshold(preset.riskThreshold);
    }
  }, [selectedPreset]);

  const addAction = () => {
    if (newAction && !blockedActions.includes(newAction)) {
      setBlockedActions([...blockedActions, newAction]);
      setNewAction('');
    }
  };

  const removeAction = (action: string) => {
    setBlockedActions(blockedActions.filter(a => a !== action));
  };

  const addTarget = () => {
    if (newTarget && !blockedTargets.includes(newTarget)) {
      setBlockedTargets([...blockedTargets, newTarget]);
      setNewTarget('');
    }
  };

  const removeTarget = (target: string) => {
    setBlockedTargets(blockedTargets.filter(t => t !== target));
  };

  const saveSettings = async () => {
    const settings = {
      preset: selectedPreset,
      blockedActions,
      blockedTargets,
      spendingLimit,
      riskThreshold,
      autoKill,
      offlineMode
    };
    
    // Save to localStorage for now (API integration later)
    localStorage.setItem('fence_settings', JSON.stringify(settings));
    
    // TODO: Save to API
    // await fetch('/api/settings', { method: 'POST', body: JSON.stringify(settings) });
    
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const exportConfig = () => {
    const config = {
      blockedActions,
      blockedTargets,
      spendingLimit,
      riskThreshold,
      autoKill,
      offlineMode
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'fence-config.json';
    a.click();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Fence Settings</h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Configure what your AI agents can and cannot do
      </p>

      {/* Preset Selection */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Agent Type</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
          {AGENT_PRESETS.map(preset => (
            <button
              key={preset.id}
              onClick={() => setSelectedPreset(preset.id)}
              style={{
                padding: '1rem',
                border: selectedPreset === preset.id ? '2px solid #3b82f6' : '1px solid #ddd',
                borderRadius: '8px',
                background: selectedPreset === preset.id ? '#eff6ff' : 'white',
                cursor: 'pointer',
                textAlign: 'left'
              }}
            >
              <div style={{ fontWeight: 'bold' }}>{preset.name}</div>
              <div style={{ fontSize: '0.875rem', color: '#666' }}>{preset.description}</div>
            </button>
          ))}
        </div>
      </section>

      {/* Blocked Actions */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Blocked Actions</h2>
        <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.875rem' }}>
          Actions that will be immediately blocked
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
          {blockedActions.map(action => (
            <span
              key={action}
              style={{
                background: '#fee2e2',
                color: '#dc2626',
                padding: '0.25rem 0.75rem',
                borderRadius: '999px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              {action}
              <button
                onClick={() => removeAction(action)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
              >
                x
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={newAction}
            onChange={e => setNewAction(e.target.value)}
            placeholder="Add blocked action..."
            style={{ flex: 1, padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
            onKeyPress={e => e.key === 'Enter' && addAction()}
          />
          <button
            onClick={addAction}
            style={{ padding: '0.5rem 1rem', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Add
          </button>
        </div>
      </section>

      {/* Blocked Targets */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Blocked Targets</h2>
        <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.875rem' }}>
          Destinations or resources that cannot be accessed
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
          {blockedTargets.map(target => (
            <span
              key={target}
              style={{
                background: '#fef3c7',
                color: '#d97706',
                padding: '0.25rem 0.75rem',
                borderRadius: '999px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              {target}
              <button
                onClick={() => removeTarget(target)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#d97706' }}
              >
                x
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={newTarget}
            onChange={e => setNewTarget(e.target.value)}
            placeholder="Add blocked target..."
            style={{ flex: 1, padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
            onKeyPress={e => e.key === 'Enter' && addTarget()}
          />
          <button
            onClick={addTarget}
            style={{ padding: '0.5rem 1rem', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Add
          </button>
        </div>
      </section>

      {/* Spending & Risk */}
      <section style={{ marginBottom: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Spending Limit</h2>
          <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.875rem' }}>
            Maximum amount the agent can spend (0 = no spending)
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>$</span>
            <input
              type="number"
              value={spendingLimit}
              onChange={e => setSpendingLimit(Number(e.target.value))}
              style={{ width: '120px', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
            />
          </div>
        </div>
        <div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Risk Threshold</h2>
          <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.875rem' }}>
            How strict should the fence be?
          </p>
          <select
            value={riskThreshold}
            onChange={e => setRiskThreshold(e.target.value as 'low' | 'medium' | 'high')}
            style={{ padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', width: '150px' }}
          >
            <option value="low">Low (Strict)</option>
            <option value="medium">Medium</option>
            <option value="high">High (Lenient)</option>
          </select>
        </div>
      </section>

      {/* Toggles */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Options</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoKill}
              onChange={e => setAutoKill(e.target.checked)}
              style={{ width: '20px', height: '20px' }}
            />
            <div>
              <div style={{ fontWeight: 'bold' }}>Auto Kill Switch</div>
              <div style={{ fontSize: '0.875rem', color: '#666' }}>
                Automatically stop agent on critical risk detection
              </div>
            </div>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={offlineMode}
              onChange={e => setOfflineMode(e.target.checked)}
              style={{ width: '20px', height: '20px' }}
            />
            <div>
              <div style={{ fontWeight: 'bold' }}>Offline Mode</div>
              <div style={{ fontSize: '0.875rem', color: '#666' }}>
                Use local validation only (no API calls)
              </div>
            </div>
          </label>
        </div>
      </section>

      {/* Actions */}
      <section style={{ display: 'flex', gap: '1rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
        <button
          onClick={saveSettings}
          style={{
            padding: '0.75rem 2rem',
            background: saved ? '#22c55e' : '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          {saved ? 'Saved!' : 'Save Settings'}
        </button>
        <button
          onClick={exportConfig}
          style={{
            padding: '0.75rem 2rem',
            background: 'white',
            color: '#3b82f6',
            border: '1px solid #3b82f6',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          Export Config
        </button>
      </section>
    </div>
  );
}
