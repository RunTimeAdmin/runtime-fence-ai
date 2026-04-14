import { CircuitBreakerState } from './types';

export interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeout: number;
  halfOpenRequests: number;
}

export class CircuitBreaker {
  private state: CircuitBreakerState = { isOpen: false, failureCount: 0 };
  private config: CircuitBreakerConfig;
  private halfOpenSuccesses = 0;

  constructor(config: Partial<CircuitBreakerConfig> = {}) {
    this.config = {
      failureThreshold: config.failureThreshold ?? 5,
      resetTimeout: config.resetTimeout ?? 60000,
      halfOpenRequests: config.halfOpenRequests ?? 3,
    };
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.isOpen()) {
      if (this.shouldAttemptReset()) {
        return this.attemptHalfOpen(fn);
      }
      throw new Error('Circuit breaker is open');
    }
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private isOpen(): boolean {
    return this.state.isOpen;
  }

  private shouldAttemptReset(): boolean {
    if (!this.state.resetAt) return false;
    return Date.now() >= this.state.resetAt;
  }

  private async attemptHalfOpen<T>(fn: () => Promise<T>): Promise<T> {
    try {
      const result = await fn();
      this.halfOpenSuccesses++;
      if (this.halfOpenSuccesses >= this.config.halfOpenRequests) {
        this.reset();
      }
      return result;
    } catch (error) {
      this.trip();
      throw error;
    }
  }

  private onSuccess(): void {
    this.state.failureCount = 0;
  }

  private onFailure(): void {
    this.state.failureCount++;
    this.state.lastFailure = Date.now();
    if (this.state.failureCount >= this.config.failureThreshold) {
      this.trip();
    }
  }

  private trip(): void {
    this.state.isOpen = true;
    this.state.resetAt = Date.now() + this.config.resetTimeout;
    this.halfOpenSuccesses = 0;
  }

  reset(): void {
    this.state = { isOpen: false, failureCount: 0 };
    this.halfOpenSuccesses = 0;
  }

  getState(): CircuitBreakerState {
    return { ...this.state };
  }
}
