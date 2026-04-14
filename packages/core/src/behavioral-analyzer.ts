import { BehavioralProfile, TransactionRequest, RiskLevel } from './types';

export class BehavioralAnalyzer {
  private profiles: Map<string, BehavioralProfile> = new Map();
  private transactionHistory: Map<string, TransactionRequest[]> = new Map();
  private readonly historyLimit = 1000;

  analyzeTransaction(tx: TransactionRequest): { anomalyScore: number; flags: string[] } {
    const profile = this.getOrCreateProfile(tx.agentId);
    const history = this.transactionHistory.get(tx.agentId) || [];
    const flags: string[] = [];
    let anomalyScore = 0;

    if (tx.amount && profile.averageTransactionSize > 0) {
      const sizeRatio = tx.amount / profile.averageTransactionSize;
      if (sizeRatio > 10) { anomalyScore += 40; flags.push('unusually_large_transaction'); }
      else if (sizeRatio > 5) { anomalyScore += 20; flags.push('large_transaction'); }
    }

    const recentTxs = history.filter(h => h.timestamp > Date.now() - 60000);
    if (recentTxs.length > profile.transactionFrequency * 2) {
      anomalyScore += 30; flags.push('high_frequency');
    }

    if (!profile.commonTargets.includes(tx.target)) {
      anomalyScore += 15; flags.push('new_target');
    }

    this.updateProfile(tx);
    return { anomalyScore: Math.min(anomalyScore, 100), flags };
  }

  private getOrCreateProfile(agentId: string): BehavioralProfile {
    if (!this.profiles.has(agentId)) {
      this.profiles.set(agentId, {
        agentId, averageTransactionSize: 0, transactionFrequency: 0,
        commonTargets: [], anomalyScore: 0, lastUpdated: Date.now()
      });
    }
    return this.profiles.get(agentId)!;
  }

  private updateProfile(tx: TransactionRequest): void {
    const profile = this.profiles.get(tx.agentId)!;
    const history = this.transactionHistory.get(tx.agentId) || [];
    history.push(tx);
    if (history.length > this.historyLimit) history.shift();
    this.transactionHistory.set(tx.agentId, history);

    if (tx.amount) {
      const amounts = history.filter(h => h.amount).map(h => h.amount!);
      profile.averageTransactionSize = amounts.reduce((a, b) => a + b, 0) / amounts.length;
    }

    const hourAgo = Date.now() - 3600000;
    profile.transactionFrequency = history.filter(h => h.timestamp > hourAgo).length;

    const targetCounts = new Map<string, number>();
    history.forEach(h => targetCounts.set(h.target, (targetCounts.get(h.target) || 0) + 1));
    profile.commonTargets = [...targetCounts.entries()]
      .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([t]) => t);
    profile.lastUpdated = Date.now();
  }

  getProfile(agentId: string): BehavioralProfile | undefined {
    return this.profiles.get(agentId);
  }

  getRiskLevel(anomalyScore: number): RiskLevel {
    if (anomalyScore >= 80) return 'critical';
    if (anomalyScore >= 50) return 'high';
    if (anomalyScore >= 25) return 'medium';
    return 'low';
  }
}
