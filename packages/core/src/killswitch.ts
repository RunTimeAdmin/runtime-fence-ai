import { AgentConfig, KillSwitchConfig, TransactionRequest, ValidationResult, KillSwitchEvent, RiskLevel, AgentStatus } from './types';
import { CircuitBreaker } from './circuit-breaker';
import { BehavioralAnalyzer } from './behavioral-analyzer';

export class KillSwitch {
  private config: KillSwitchConfig;
  private agents: Map<string, AgentConfig> = new Map();
  private agentStatus: Map<string, AgentStatus> = new Map();
  private circuitBreaker: CircuitBreaker;
  private behavioralAnalyzer: BehavioralAnalyzer;
  private eventListeners: ((event: KillSwitchEvent) => void)[] = [];
  private globalKillActive = false;

  constructor(config: Partial<KillSwitchConfig> = {}) {
    this.config = {
      enabled: config.enabled ?? true,
      autoTriggerThreshold: config.autoTriggerThreshold ?? 'critical',
      cooldownPeriod: config.cooldownPeriod ?? 300000,
      requireMultiSig: config.requireMultiSig ?? false,
      notifyOnTrigger: config.notifyOnTrigger ?? true,
      webhookUrl: config.webhookUrl
    };
    this.circuitBreaker = new CircuitBreaker();
    this.behavioralAnalyzer = new BehavioralAnalyzer();
  }

  registerAgent(agent: AgentConfig): void {
    this.agents.set(agent.id, agent);
    this.agentStatus.set(agent.id, 'active');
  }

  async validate(tx: TransactionRequest): Promise<ValidationResult> {
    if (this.globalKillActive) {
      return { allowed: false, riskScore: 100, riskLevel: 'critical', reasons: ['Global kill switch active'], recommendations: ['Wait for system reset'] };
    }
    const status = this.agentStatus.get(tx.agentId);
    if (!status || status !== 'active') {
      return { allowed: false, riskScore: 100, riskLevel: 'critical', reasons: ['Agent not active'], recommendations: ['Register or reactivate agent'] };
    }
    const agent = this.agents.get(tx.agentId);
    if (!agent) {
      return { allowed: false, riskScore: 100, riskLevel: 'critical', reasons: ['Agent not found'], recommendations: ['Register agent first'] };
    }
    const reasons: string[] = [];
    const recommendations: string[] = [];
    let riskScore = 0;

    if (agent.allowedTargets && !agent.allowedTargets.includes(tx.target)) {
      riskScore += 50; reasons.push('Target not in allowlist');
    }
    if (agent.spendingLimit && tx.amount && tx.amount > agent.spendingLimit) {
      riskScore += 40; reasons.push('Exceeds spending limit');
    }
    const behavior = this.behavioralAnalyzer.analyzeTransaction(tx);
    riskScore += behavior.anomalyScore * 0.5;
    reasons.push(...behavior.flags);

    const riskLevel = this.getRiskLevel(riskScore);
    const allowed = riskScore < this.getRiskThreshold();

    if (!allowed && this.shouldAutoTrigger(riskLevel)) {
      this.triggerKillSwitch(tx.agentId, 'automatic', reasons.join(', '));
    }
    return { allowed, riskScore: Math.min(riskScore, 100), riskLevel, reasons, recommendations };
  }

  triggerKillSwitch(agentId: string | null, trigger: 'manual' | 'automatic' | 'policy' | 'emergency', reason: string): void {
    if (agentId) {
      this.agentStatus.set(agentId, 'suspended');
    } else {
      this.globalKillActive = true;
    }
    this.emitEvent({ type: 'triggered', agentId: agentId || undefined, trigger, reason, timestamp: Date.now() });
  }

  resetKillSwitch(agentId?: string): void {
    if (agentId) {
      this.agentStatus.set(agentId, 'active');
    } else {
      this.globalKillActive = false;
    }
    this.emitEvent({ type: 'reset', agentId, trigger: 'manual', reason: 'Manual reset', timestamp: Date.now() });
  }

  private getRiskLevel(score: number): RiskLevel {
    if (score >= 80) return 'critical';
    if (score >= 50) return 'high';
    if (score >= 25) return 'medium';
    return 'low';
  }

  private getRiskThreshold(): number {
    const thresholds: Record<RiskLevel, number> = { low: 25, medium: 50, high: 75, critical: 90 };
    return thresholds[this.config.autoTriggerThreshold];
  }

  private shouldAutoTrigger(riskLevel: RiskLevel): boolean {
    const levels: RiskLevel[] = ['low', 'medium', 'high', 'critical'];
    return levels.indexOf(riskLevel) >= levels.indexOf(this.config.autoTriggerThreshold);
  }

  onEvent(listener: (event: KillSwitchEvent) => void): void { this.eventListeners.push(listener); }
  private emitEvent(event: KillSwitchEvent): void { this.eventListeners.forEach(l => l(event)); }
  getAgentStatus(agentId: string): AgentStatus { return this.agentStatus.get(agentId) || 'unknown'; }
  isGlobalKillActive(): boolean { return this.globalKillActive; }
}
