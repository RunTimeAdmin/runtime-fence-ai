// Type definitions for AI Agent Kill Switch

export type AgentStatus = 'active' | 'suspended' | 'terminated' | 'unknown';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type TriggerType = 'manual' | 'automatic' | 'policy' | 'emergency';

export interface AgentConfig {
  id: string;
  name: string;
  owner: string;
  permissions: string[];
  spendingLimit?: number;
  rateLimit?: number;
  allowedTargets?: string[];
}

export interface KillSwitchConfig {
  enabled: boolean;
  autoTriggerThreshold: RiskLevel;
  cooldownPeriod: number;
  requireMultiSig: boolean;
  notifyOnTrigger: boolean;
  webhookUrl?: string;
}

export interface TransactionRequest {
  agentId: string;
  action: string;
  target: string;
  amount?: number;
  data?: Record<string, unknown>;
  timestamp: number;
}

export interface ValidationResult {
  allowed: boolean;
  riskScore: number;
  riskLevel: RiskLevel;
  reasons: string[];
  recommendations: string[];
}

export interface CircuitBreakerState {
  isOpen: boolean;
  failureCount: number;
  lastFailure?: number;
  resetAt?: number;
}

export interface BehavioralProfile {
  agentId: string;
  averageTransactionSize: number;
  transactionFrequency: number;
  commonTargets: string[];
  anomalyScore: number;
  lastUpdated: number;
}

export interface KillSwitchEvent {
  type: 'activated' | 'deactivated' | 'triggered' | 'reset';
  agentId?: string;
  trigger: TriggerType;
  reason: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}
