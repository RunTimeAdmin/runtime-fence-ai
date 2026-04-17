import { KillSwitch } from './killswitch';
import { AgentConfig, TransactionRequest } from './types';

describe('KillSwitch', () => {
  let killSwitch: KillSwitch;

  beforeEach(() => {
    killSwitch = new KillSwitch();
  });

  afterEach(() => {
    // Reset global kill state if needed
    if (killSwitch.isGlobalKillActive()) {
      killSwitch.resetKillSwitch();
    }
  });

  describe('registerAgent', () => {
    it('should register a new agent', () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read', 'write']
      };

      killSwitch.registerAgent(agent);
      const status = killSwitch.getAgentStatus('agent-1');

      expect(status).toBe('active');
    });

    it('should update agent registration when called with same id', () => {
      const agent1: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent 1',
        owner: 'user-1',
        permissions: ['read']
      };

      const agent2: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent 2',
        owner: 'user-1',
        permissions: ['read', 'write']
      };

      killSwitch.registerAgent(agent1);
      killSwitch.registerAgent(agent2);

      const status = killSwitch.getAgentStatus('agent-1');
      expect(status).toBe('active');
    });
  });

  describe('triggerKillSwitch', () => {
    it('should kill a specific agent', () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch('agent-1', 'manual', 'Test kill');

      const status = killSwitch.getAgentStatus('agent-1');
      expect(status).toBe('suspended');
    });

    it('should trigger global kill when agentId is null', () => {
      const agent1: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent 1',
        owner: 'user-1',
        permissions: ['read']
      };

      const agent2: AgentConfig = {
        id: 'agent-2',
        name: 'Test Agent 2',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent1);
      killSwitch.registerAgent(agent2);
      killSwitch.triggerKillSwitch(null, 'emergency', 'Global kill');

      expect(killSwitch.isGlobalKillActive()).toBe(true);
    });

    it('should emit event when kill switch is triggered', () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      const eventHandler = jest.fn();
      killSwitch.onEvent(eventHandler);

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch('agent-1', 'manual', 'Test kill');

      expect(eventHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'triggered',
          agentId: 'agent-1',
          trigger: 'manual',
          reason: 'Test kill'
        })
      );
    });
  });

  describe('validate', () => {
    it('should allow action for active agent', async () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read'],
        allowedTargets: ['/tmp/test.txt']
      };

      killSwitch.registerAgent(agent);

      const tx: TransactionRequest = {
        agentId: 'agent-1',
        action: 'read_file',
        target: '/tmp/test.txt',
        timestamp: Date.now()
      };

      const result = await killSwitch.validate(tx);

      expect(result.allowed).toBe(true);
      expect(result.riskScore).toBeLessThan(100);
    });

    it('should block action for killed agent', async () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch('agent-1', 'emergency', 'Test');

      const tx: TransactionRequest = {
        agentId: 'agent-1',
        action: 'read_file',
        target: '/tmp/test.txt',
        timestamp: Date.now()
      };

      const result = await killSwitch.validate(tx);

      expect(result.allowed).toBe(false);
      expect(result.riskScore).toBe(100);
    });

    it('should block action when global kill is active', async () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch(null, 'emergency', 'Global kill');

      const tx: TransactionRequest = {
        agentId: 'agent-1',
        action: 'read_file',
        target: '/tmp/test.txt',
        timestamp: Date.now()
      };

      const result = await killSwitch.validate(tx);

      expect(result.allowed).toBe(false);
      expect(result.riskScore).toBe(100);
      expect(result.reasons).toContain('Global kill switch active');
    });

    it('should return risk score 100 for unknown agent', async () => {
      const tx: TransactionRequest = {
        agentId: 'unknown-agent',
        action: 'read_file',
        target: '/tmp/test.txt',
        timestamp: Date.now()
      };

      const result = await killSwitch.validate(tx);

      expect(result.riskScore).toBe(100);
      expect(result.allowed).toBe(false);
      // The KillSwitch returns 'Agent not active' when agent status is not 'active'
      // (which includes unknown agents that were never registered)
      expect(result.reasons.some(r => r.includes('Agent'))).toBe(true);
    });

    it('should increase risk score for target not in allowlist', async () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read'],
        allowedTargets: ['/allowed/path']
      };

      killSwitch.registerAgent(agent);

      const tx: TransactionRequest = {
        agentId: 'agent-1',
        action: 'read_file',
        target: '/unauthorized/path',
        timestamp: Date.now()
      };

      const result = await killSwitch.validate(tx);

      expect(result.reasons).toContain('Target not in allowlist');
      expect(result.riskScore).toBeGreaterThan(0);
    });

    it('should increase risk score for exceeding spending limit', async () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['transfer'],
        spendingLimit: 100
      };

      killSwitch.registerAgent(agent);

      const tx: TransactionRequest = {
        agentId: 'agent-1',
        action: 'transfer',
        target: 'recipient-1',
        amount: 500,
        timestamp: Date.now()
      };

      const result = await killSwitch.validate(tx);

      expect(result.reasons).toContain('Exceeds spending limit');
      expect(result.riskScore).toBeGreaterThan(0);
    });
  });

  describe('resetKillSwitch', () => {
    it('should reset a killed agent', () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch('agent-1', 'emergency', 'Test');
      killSwitch.resetKillSwitch('agent-1');

      const status = killSwitch.getAgentStatus('agent-1');
      expect(status).toBe('active');
    });

    it('should reset global kill when no agentId provided', () => {
      killSwitch.triggerKillSwitch(null, 'emergency', 'Global kill');
      expect(killSwitch.isGlobalKillActive()).toBe(true);

      killSwitch.resetKillSwitch();
      expect(killSwitch.isGlobalKillActive()).toBe(false);
    });

    it('should emit event when kill switch is reset', () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      const eventHandler = jest.fn();
      killSwitch.onEvent(eventHandler);

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch('agent-1', 'manual', 'Test kill');
      killSwitch.resetKillSwitch('agent-1');

      expect(eventHandler).toHaveBeenLastCalledWith(
        expect.objectContaining({
          type: 'reset',
          agentId: 'agent-1',
          trigger: 'manual',
          reason: 'Manual reset'
        })
      );
    });
  });

  describe('getAgentStatus', () => {
    it('should return unknown for unregistered agent', () => {
      const status = killSwitch.getAgentStatus('non-existent-agent');
      expect(status).toBe('unknown');
    });

    it('should return active for newly registered agent', () => {
      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent);
      const status = killSwitch.getAgentStatus('agent-1');

      expect(status).toBe('active');
    });
  });

  describe('isGlobalKillActive', () => {
    it('should return false by default', () => {
      expect(killSwitch.isGlobalKillActive()).toBe(false);
    });

    it('should return true after global kill is triggered', () => {
      killSwitch.triggerKillSwitch(null, 'emergency', 'Global kill');
      expect(killSwitch.isGlobalKillActive()).toBe(true);
    });
  });

  describe('onEvent', () => {
    it('should allow multiple event listeners', () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();

      killSwitch.onEvent(handler1);
      killSwitch.onEvent(handler2);

      const agent: AgentConfig = {
        id: 'agent-1',
        name: 'Test Agent',
        owner: 'user-1',
        permissions: ['read']
      };

      killSwitch.registerAgent(agent);
      killSwitch.triggerKillSwitch('agent-1', 'manual', 'Test');

      expect(handler1).toHaveBeenCalled();
      expect(handler2).toHaveBeenCalled();
    });
  });
});
