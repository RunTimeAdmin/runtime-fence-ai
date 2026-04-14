import { KillSwitch, AgentConfig, TransactionRequest, ValidationResult, KillSwitchConfig } from '@killswitch/core';

export class KillSwitchClient {
  private apiUrl: string;
  private apiKey?: string;

  constructor(options: { apiUrl?: string; apiKey?: string } = {}) {
    this.apiUrl = options.apiUrl || 'http://localhost:3001';
    this.apiKey = options.apiKey;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.apiKey) headers['Authorization'] = 'Bearer ' + this.apiKey;
    const res = await fetch(this.apiUrl + endpoint, { ...options, headers: { ...headers, ...options.headers as Record<string,string> } });
    if (!res.ok) throw new Error('API Error: ' + res.status);
    return res.json() as Promise<T>;
  }

  async registerAgent(agent: AgentConfig): Promise<{ success: boolean; agentId: string }> {
    return this.request('/api/v1/agents', { method: 'POST', body: JSON.stringify(agent) });
  }

  async validate(tx: TransactionRequest): Promise<ValidationResult> {
    return this.request('/api/v1/validate', { method: 'POST', body: JSON.stringify(tx) });
  }

  async triggerKillSwitch(agentId?: string, reason?: string): Promise<{ success: boolean }> {
    return this.request('/api/v1/killswitch/trigger', { method: 'POST', body: JSON.stringify({ agentId, reason }) });
  }

  async resetKillSwitch(agentId?: string): Promise<{ success: boolean }> {
    return this.request('/api/v1/killswitch/reset', { method: 'POST', body: JSON.stringify({ agentId }) });
  }

  async getStatus(): Promise<{ globalKillActive: boolean }> {
    return this.request('/api/v1/killswitch/status');
  }

  async getAgentStatus(agentId: string): Promise<{ agentId: string; status: string }> {
    return this.request('/api/v1/agents/' + agentId + '/status');
  }
}

export * from '@killswitch/core';
export default KillSwitchClient;
