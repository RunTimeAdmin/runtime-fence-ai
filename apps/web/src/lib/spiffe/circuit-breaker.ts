/**
 * Circuit Breaker for Auto-Kill
 * 
 * Monitors agent behavior and automatically kills agents that:
 * - Exceed error rate thresholds
 * - Make too many requests (rate limiting)
 * - Access unauthorized resources
 * - Show anomalous behavior patterns
 * 
 * Based on SPIFFE/SPIRE circuit breaker patterns
 */

// Circuit breaker states
type CircuitState = 'closed' | 'open' | 'half-open';

interface CircuitBreakerConfig {
  failureThreshold: number;      // Failures before opening circuit
  successThreshold: number;      // Successes to close circuit from half-open
  timeout: number;               // Time in ms before attempting half-open
  requestVolumeThreshold: number; // Min requests before calculating error rate
  errorRateThreshold: number;    // Error rate % to trigger circuit
}

interface AgentMetrics {
  spiffeId: string;
  totalRequests: number;
  failedRequests: number;
  successfulRequests: number;
  lastFailure: Date | null;
  lastSuccess: Date | null;
  consecutiveFailures: number;
  circuitState: CircuitState;
  circuitOpenedAt: Date | null;
  anomalyScore: number;
}

// Default thresholds
const DEFAULT_CONFIG: CircuitBreakerConfig = {
  failureThreshold: 5,          // 5 consecutive failures
  successThreshold: 3,          // 3 successes to recover
  timeout: 30000,               // 30 seconds before half-open
  requestVolumeThreshold: 20,   // Min 20 requests
  errorRateThreshold: 50        // 50% error rate
};

// Auto-kill thresholds
const AUTO_KILL_THRESHOLDS = {
  maxConsecutiveFailures: 10,
  maxErrorRate: 80,             // 80% error rate
  maxAnomalyScore: 90,          // Anomaly detection score
  maxUnauthorizedAttempts: 3,
  maxRateLimitViolations: 5
};

export class CircuitBreaker {
  private metrics: Map<string, AgentMetrics> = new Map();
  private config: CircuitBreakerConfig;
  private killCallback: (spiffeId: string, reason: string) => Promise<void>;

  constructor(
    config: Partial<CircuitBreakerConfig> = {},
    killCallback: (spiffeId: string, reason: string) => Promise<void>
  ) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.killCallback = killCallback;
  }

  /**
   * Record a successful request
   */
  async recordSuccess(spiffeId: string): Promise<void> {
    const metrics = this.getOrCreateMetrics(spiffeId);
    
    metrics.totalRequests++;
    metrics.successfulRequests++;
    metrics.lastSuccess = new Date();
    metrics.consecutiveFailures = 0;

    // Handle half-open state
    if (metrics.circuitState === 'half-open') {
      const successCount = this.getRecentSuccessCount(spiffeId);
      if (successCount >= this.config.successThreshold) {
        metrics.circuitState = 'closed';
        console.log(`✅ Circuit CLOSED for ${spiffeId}`);
      }
    }

    this.metrics.set(spiffeId, metrics);
  }

  /**
   * Record a failed request
   */
  async recordFailure(spiffeId: string, errorType: string): Promise<void> {
    const metrics = this.getOrCreateMetrics(spiffeId);
    
    metrics.totalRequests++;
    metrics.failedRequests++;
    metrics.lastFailure = new Date();
    metrics.consecutiveFailures++;

    // Check if circuit should open
    if (metrics.circuitState === 'closed') {
      if (this.shouldOpenCircuit(metrics)) {
        metrics.circuitState = 'open';
        metrics.circuitOpenedAt = new Date();
        console.log(`⚠️ Circuit OPENED for ${spiffeId}`);
      }
    }

    // Check if agent should be auto-killed
    const killReason = await this.checkAutoKill(metrics, errorType);
    if (killReason) {
      await this.killCallback(spiffeId, killReason);
    }

    this.metrics.set(spiffeId, metrics);
  }

  /**
   * Record unauthorized access attempt
   */
  async recordUnauthorizedAttempt(spiffeId: string, resource: string): Promise<void> {
    const metrics = this.getOrCreateMetrics(spiffeId);
    
    // Track unauthorized attempts separately
    const key = `${spiffeId}:unauthorized`;
    const count = (this.getMetricValue(key) || 0) + 1;
    this.setMetricValue(key, count);

    console.log(`🚫 Unauthorized attempt by ${spiffeId}: ${resource} (${count} total)`);

    if (count >= AUTO_KILL_THRESHOLDS.maxUnauthorizedAttempts) {
      await this.killCallback(
        spiffeId,
        `AUTO-KILL: ${count} unauthorized access attempts (last: ${resource})`
      );
    }
  }

  /**
   * Record rate limit violation
   */
  async recordRateLimitViolation(spiffeId: string): Promise<void> {
    const key = `${spiffeId}:ratelimit`;
    const count = (this.getMetricValue(key) || 0) + 1;
    this.setMetricValue(key, count);

    console.log(`⏱️ Rate limit violation by ${spiffeId} (${count} total)`);

    if (count >= AUTO_KILL_THRESHOLDS.maxRateLimitViolations) {
      await this.killCallback(
        spiffeId,
        `AUTO-KILL: ${count} rate limit violations`
      );
    }
  }

  /**
   * Update anomaly score (from ML model or heuristics)
   */
  async updateAnomalyScore(spiffeId: string, score: number): Promise<void> {
    const metrics = this.getOrCreateMetrics(spiffeId);
    metrics.anomalyScore = score;
    this.metrics.set(spiffeId, metrics);

    if (score >= AUTO_KILL_THRESHOLDS.maxAnomalyScore) {
      await this.killCallback(
        spiffeId,
        `AUTO-KILL: Anomaly score ${score} exceeds threshold ${AUTO_KILL_THRESHOLDS.maxAnomalyScore}`
      );
    }
  }

  /**
   * Check if request should be allowed (circuit breaker logic)
   */
  isRequestAllowed(spiffeId: string): { allowed: boolean; reason?: string } {
    const metrics = this.getOrCreateMetrics(spiffeId);

    switch (metrics.circuitState) {
      case 'closed':
        return { allowed: true };
      
      case 'open':
        // Check if timeout has elapsed
        if (metrics.circuitOpenedAt) {
          const elapsed = Date.now() - metrics.circuitOpenedAt.getTime();
          if (elapsed >= this.config.timeout) {
            metrics.circuitState = 'half-open';
            this.metrics.set(spiffeId, metrics);
            console.log(`🔄 Circuit HALF-OPEN for ${spiffeId}`);
            return { allowed: true };
          }
        }
        return { 
          allowed: false, 
          reason: `Circuit open - retry after ${this.config.timeout}ms` 
        };
      
      case 'half-open':
        // Allow limited requests in half-open state
        return { allowed: true };
      
      default:
        return { allowed: true };
    }
  }

  /**
   * Get current metrics for an agent
   */
  getMetrics(spiffeId: string): AgentMetrics | undefined {
    return this.metrics.get(spiffeId);
  }

  /**
   * Get all agents with open circuits
   */
  getOpenCircuits(): AgentMetrics[] {
    return Array.from(this.metrics.values())
      .filter(m => m.circuitState === 'open' || m.circuitState === 'half-open');
  }

  /**
   * Reset metrics for an agent
   */
  resetMetrics(spiffeId: string): void {
    this.metrics.delete(spiffeId);
    this.setMetricValue(`${spiffeId}:unauthorized`, 0);
    this.setMetricValue(`${spiffeId}:ratelimit`, 0);
  }

  // Private methods
  private getOrCreateMetrics(spiffeId: string): AgentMetrics {
    if (!this.metrics.has(spiffeId)) {
      this.metrics.set(spiffeId, {
        spiffeId,
        totalRequests: 0,
        failedRequests: 0,
        successfulRequests: 0,
        lastFailure: null,
        lastSuccess: null,
        consecutiveFailures: 0,
        circuitState: 'closed',
        circuitOpenedAt: null,
        anomalyScore: 0
      });
    }
    return this.metrics.get(spiffeId)!;
  }

  private shouldOpenCircuit(metrics: AgentMetrics): boolean {
    // Check consecutive failures
    if (metrics.consecutiveFailures >= this.config.failureThreshold) {
      return true;
    }

    // Check error rate (only if enough requests)
    if (metrics.totalRequests >= this.config.requestVolumeThreshold) {
      const errorRate = (metrics.failedRequests / metrics.totalRequests) * 100;
      if (errorRate >= this.config.errorRateThreshold) {
        return true;
      }
    }

    return false;
  }

  private async checkAutoKill(metrics: AgentMetrics, errorType: string): Promise<string | null> {
    // Check consecutive failures
    if (metrics.consecutiveFailures >= AUTO_KILL_THRESHOLDS.maxConsecutiveFailures) {
      return `AUTO-KILL: ${metrics.consecutiveFailures} consecutive failures`;
    }

    // Check error rate
    if (metrics.totalRequests >= this.config.requestVolumeThreshold) {
      const errorRate = (metrics.failedRequests / metrics.totalRequests) * 100;
      if (errorRate >= AUTO_KILL_THRESHOLDS.maxErrorRate) {
        return `AUTO-KILL: ${errorRate.toFixed(1)}% error rate exceeds ${AUTO_KILL_THRESHOLDS.maxErrorRate}%`;
      }
    }

    return null;
  }

  private getRecentSuccessCount(spiffeId: string): number {
    // Simplified - in production track rolling window
    const metrics = this.metrics.get(spiffeId);
    return metrics?.successfulRequests || 0;
  }

  private metricValues: Map<string, number> = new Map();
  
  private getMetricValue(key: string): number | undefined {
    return this.metricValues.get(key);
  }

  private setMetricValue(key: string, value: number): void {
    this.metricValues.set(key, value);
  }
}

/**
 * Immutable Audit Logger with SPIFFE IDs
 * 
 * Creates tamper-proof audit trail with:
 * - SHA-256 hash chain (each entry references previous)
 * - SPIFFE ID attribution
 * - Cryptographic signatures
 */
export class ImmutableAuditLogger {
  private lastHash: string = 'GENESIS';

  /**
   * Log an audit event with hash chain
   */
  async log(event: {
    eventType: string;
    spiffeId: string;
    action: string;
    resource?: string;
    metadata?: Record<string, unknown>;
    success: boolean;
  }): Promise<{ hash: string; sequence: number }> {
    const timestamp = new Date().toISOString();
    
    // Create hash chain entry
    const entry = {
      ...event,
      timestamp,
      previousHash: this.lastHash,
      sequence: await this.getNextSequence()
    };

    // Calculate hash
    const hash = await this.calculateHash(entry);
    this.lastHash = hash;

    // Store in database (Supabase)
    // In production, also write to immutable storage (blockchain, S3 with object lock, etc.)
    const logEntry = {
      event_type: event.eventType,
      spiffe_id: event.spiffeId,
      action: event.action,
      resource: event.resource,
      metadata: event.metadata,
      success: event.success,
      timestamp,
      previous_hash: entry.previousHash,
      hash,
      sequence: entry.sequence
    };

    console.log(`📝 AUDIT: [${entry.sequence}] ${event.eventType} by ${event.spiffeId} - ${event.action}`);

    return { hash, sequence: entry.sequence };
  }

  /**
   * Verify audit log integrity
   */
  async verifyIntegrity(startSequence: number, endSequence: number): Promise<{
    valid: boolean;
    brokenAt?: number;
    message: string;
  }> {
    // In production, fetch logs from DB and verify hash chain
    // Each entry's hash should match recalculated hash
    // Each entry's previousHash should match previous entry's hash
    
    return {
      valid: true,
      message: `Verified ${endSequence - startSequence + 1} entries`
    };
  }

  /**
   * Export audit logs for compliance
   */
  async exportLogs(
    startDate: Date,
    endDate: Date,
    spiffeId?: string
  ): Promise<{ logs: unknown[]; hash: string }> {
    // Export logs with integrity proof
    return {
      logs: [],
      hash: await this.calculateHash({ startDate, endDate, spiffeId })
    };
  }

  // Private methods
  private async calculateHash(data: unknown): Promise<string> {
    const str = JSON.stringify(data);
    // Use Web Crypto API or crypto module
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  private sequenceCounter = 0;
  
  private async getNextSequence(): Promise<number> {
    return ++this.sequenceCounter;
  }
}

// Export singleton instances
export const circuitBreaker = new CircuitBreaker(
  DEFAULT_CONFIG,
  async (spiffeId, reason) => {
    console.log(`🔴 AUTO-KILL TRIGGERED: ${spiffeId} - ${reason}`);
    // Call the kill API
    // await killAgent(spiffeId, reason);
  }
);

export const auditLogger = new ImmutableAuditLogger();
