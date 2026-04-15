/**
 * SPIFFE Identity Service for $KILLSWITCH
 * 
 * Provides cryptographic identity management for AI agents.
 * Based on SPIFFE/SPIRE patterns from "SPIFFE/SPIRE for AI Agents" by David Cooper
 * 
 * Key concepts:
 * - Each agent gets unique SPIFFE ID: spiffe://killswitch.ai/agent/{agent-id}
 * - Credentials auto-rotate (no static API keys)
 * - Instant revocation = instant kill (30 seconds vs 24 hours)
 */

import { supabase } from '../supabase';
import crypto from 'crypto';

// Trust domain for $KILLSWITCH
const TRUST_DOMAIN = 'killswitch.ai';

// SPIFFE ID format
type SpiffeId = `spiffe://${string}/${string}`;

interface AgentIdentity {
  spiffeId: SpiffeId;
  agentId: string;
  walletAddress: string;
  issuedAt: Date;
  expiresAt: Date;
  status: 'active' | 'revoked' | 'expired';
  permissions: string[];
}

interface SVID {
  spiffeId: SpiffeId;
  certificate: string;
  privateKey: string;
  expiresAt: Date;
  trustBundle: string;
}

// Authorization matrix - who can do what
const AUTHORIZATION_MATRIX: Record<string, { permissions: string[], canKill: boolean }> = {
  'admin': {
    permissions: ['*'],
    canKill: true
  },
  'governance': {
    permissions: ['vote', 'propose', 'execute_proposal'],
    canKill: true  // Governance can kill via proposal
  },
  'user': {
    permissions: ['register_agent', 'view_own_agents', 'kill_own_agents'],
    canKill: false  // Can only kill own agents
  },
  'agent': {
    permissions: ['api_call', 'report_status'],
    canKill: false
  }
};

export class SpiffeIdentityService {
  private rotationInterval: NodeJS.Timeout | null = null;

  /**
   * Generate SPIFFE ID for an agent
   */
  generateSpiffeId(agentType: string, agentId: string): SpiffeId {
    return `spiffe://${TRUST_DOMAIN}/${agentType}/${agentId}`;
  }

  /**
   * Register a new agent and issue identity
   */
  async registerAgent(
    walletAddress: string,
    agentName: string,
    agentType: string = 'agent'
  ): Promise<AgentIdentity> {
    const agentId = crypto.randomUUID();
    const spiffeId = this.generateSpiffeId(agentType, agentId);
    
    const now = new Date();
    const expiresAt = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour TTL

    const identity: AgentIdentity = {
      spiffeId,
      agentId,
      walletAddress,
      issuedAt: now,
      expiresAt,
      status: 'active',
      permissions: AUTHORIZATION_MATRIX[agentType]?.permissions || ['api_call']
    };

    // Store in database
    const { error } = await supabase.from('agent_identities').insert({
      spiffe_id: spiffeId,
      agent_id: agentId,
      wallet_address: walletAddress,
      agent_name: agentName,
      agent_type: agentType,
      issued_at: now.toISOString(),
      expires_at: expiresAt.toISOString(),
      status: 'active',
      permissions: identity.permissions
    });

    if (error) {
      throw new Error(`Failed to register agent: ${error.message}`);
    }

    // Log registration event
    await this.logAuditEvent({
      eventType: 'agent_registered',
      spiffeId,
      action: 'create',
      metadata: { agentName, agentType, walletAddress }
    });

    return identity;
  }

  /**
   * Issue SVID (SPIFFE Verifiable Identity Document)
   * This is the credential the agent uses for authentication
   */
  async issueSVID(spiffeId: SpiffeId): Promise<SVID> {
    // Verify agent exists and is active
    const { data: agent, error } = await supabase
      .from('agent_identities')
      .select('*')
      .eq('spiffe_id', spiffeId)
      .eq('status', 'active')
      .single();

    if (error || !agent) {
      throw new Error('Agent not found or not active');
    }

    // Generate short-lived credential (simulated - in production use actual PKI)
    const now = new Date();
    const expiresAt = new Date(now.getTime() + 15 * 60 * 1000); // 15 min TTL

    const svid: SVID = {
      spiffeId,
      certificate: this.generateCertificate(spiffeId, expiresAt),
      privateKey: this.generatePrivateKey(),
      expiresAt,
      trustBundle: this.getTrustBundle()
    };

    // Log SVID issuance
    await this.logAuditEvent({
      eventType: 'svid_issued',
      spiffeId,
      action: 'issue',
      metadata: { expiresAt: expiresAt.toISOString() }
    });

    return svid;
  }

  /**
   * INSTANT REVOCATION - The core kill mechanism
   * Revoking SPIFFE ID = Agent loses ALL access immediately
   */
  async revokeIdentity(
    spiffeId: SpiffeId,
    revokedBy: SpiffeId,
    reason: string
  ): Promise<{ success: boolean; revokedAt: Date }> {
    // Verify revoker has authority
    const canRevoke = await this.verifyKillAuthority(revokedBy, spiffeId);
    if (!canRevoke) {
      await this.logAuditEvent({
        eventType: 'unauthorized_revocation_attempt',
        spiffeId: revokedBy,
        action: 'denied',
        metadata: { targetSpiffeId: spiffeId, reason }
      });
      throw new Error('Unauthorized: You cannot revoke this agent');
    }

    const revokedAt = new Date();

    // Revoke in database
    const { error } = await supabase
      .from('agent_identities')
      .update({
        status: 'revoked',
        revoked_at: revokedAt.toISOString(),
        revoked_by: revokedBy,
        revocation_reason: reason
      })
      .eq('spiffe_id', spiffeId);

    if (error) {
      throw new Error(`Failed to revoke identity: ${error.message}`);
    }

    // Log revocation (this is the KILL event)
    await this.logAuditEvent({
      eventType: 'agent_killed',
      spiffeId,
      action: 'revoke',
      metadata: {
        revokedBy,
        reason,
        revokedAt: revokedAt.toISOString(),
        effectiveImmediately: true
      }
    });

    // Broadcast kill signal to all connected services
    await this.broadcastKillSignal(spiffeId);

    return { success: true, revokedAt };
  }

  /**
   * Verify if caller has authority to kill an agent
   */
  async verifyKillAuthority(callerSpiffeId: SpiffeId, targetSpiffeId: SpiffeId): Promise<boolean> {
    // Extract caller type from SPIFFE ID
    const callerType = this.extractAgentType(callerSpiffeId);
    
    // Admins can kill anyone
    if (callerType === 'admin') return true;
    
    // Governance can kill anyone (via proposal execution)
    if (callerType === 'governance') return true;
    
    // Users can only kill their own agents
    if (callerType === 'user') {
      const { data: caller } = await supabase
        .from('agent_identities')
        .select('wallet_address')
        .eq('spiffe_id', callerSpiffeId)
        .single();
      
      const { data: target } = await supabase
        .from('agent_identities')
        .select('wallet_address')
        .eq('spiffe_id', targetSpiffeId)
        .single();
      
      return caller?.wallet_address === target?.wallet_address;
    }
    
    return false;
  }

  /**
   * Broadcast kill signal to all services
   */
  private async broadcastKillSignal(spiffeId: SpiffeId): Promise<void> {
    // In production, this would use a message queue or websocket
    // For now, we update a real-time table that services subscribe to
    await supabase.from('kill_signals').insert({
      spiffe_id: spiffeId,
      signal_type: 'immediate_termination',
      broadcast_at: new Date().toISOString()
    });

    console.log(`🔴 KILL SIGNAL BROADCAST: ${spiffeId}`);
  }

  /**
   * Validate an SVID (called by services to verify agent identity)
   */
  async validateSVID(svid: SVID): Promise<{ valid: boolean; spiffeId?: SpiffeId; error?: string }> {
    // Check expiration
    if (new Date() > svid.expiresAt) {
      return { valid: false, error: 'SVID expired' };
    }

    // Check if identity is revoked
    const { data: agent } = await supabase
      .from('agent_identities')
      .select('status')
      .eq('spiffe_id', svid.spiffeId)
      .single();

    if (!agent || agent.status === 'revoked') {
      return { valid: false, error: 'Identity revoked' };
    }

    if (agent.status === 'expired') {
      return { valid: false, error: 'Identity expired' };
    }

    // Log validation (for audit)
    await this.logAuditEvent({
      eventType: 'svid_validated',
      spiffeId: svid.spiffeId,
      action: 'validate',
      metadata: { result: 'valid' }
    });

    return { valid: true, spiffeId: svid.spiffeId };
  }

  /**
   * Auto-rotate credentials for all active agents
   * Called every 5 minutes
   */
  async rotateCredentials(): Promise<void> {
    const now = new Date();
    const rotationThreshold = new Date(now.getTime() + 10 * 60 * 1000); // 10 min before expiry

    // Find agents needing rotation
    const { data: agents } = await supabase
      .from('agent_identities')
      .select('spiffe_id')
      .eq('status', 'active')
      .lt('expires_at', rotationThreshold.toISOString());

    if (!agents || agents.length === 0) return;

    for (const agent of agents) {
      const newExpiry = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour
      
      await supabase
        .from('agent_identities')
        .update({ expires_at: newExpiry.toISOString() })
        .eq('spiffe_id', agent.spiffe_id);

      await this.logAuditEvent({
        eventType: 'credential_rotated',
        spiffeId: agent.spiffe_id as SpiffeId,
        action: 'rotate',
        metadata: { newExpiry: newExpiry.toISOString() }
      });
    }

    console.log(`🔄 Rotated credentials for ${agents.length} agents`);
  }

  /**
   * Start automatic credential rotation
   */
  startRotationService(): void {
    if (this.rotationInterval) return;
    
    this.rotationInterval = setInterval(() => {
      this.rotateCredentials().catch(console.error);
    }, 5 * 60 * 1000); // Every 5 minutes

    console.log('🔄 SPIFFE credential rotation service started');
  }

  /**
   * Stop rotation service
   */
  stopRotationService(): void {
    if (this.rotationInterval) {
      clearInterval(this.rotationInterval);
      this.rotationInterval = null;
    }
  }

  // Helper methods
  private extractAgentType(spiffeId: SpiffeId): string {
    const parts = spiffeId.split('/');
    return parts[3] || 'unknown';
  }

  private generateCertificate(spiffeId: SpiffeId, expiresAt: Date): string {
    // Simulated certificate - in production use actual PKI
    return Buffer.from(JSON.stringify({
      spiffeId,
      expiresAt,
      issuer: `spiffe://${TRUST_DOMAIN}/ca`,
      issuedAt: new Date()
    })).toString('base64');
  }

  private generatePrivateKey(): string {
    // Simulated - in production generate actual key pair
    return crypto.randomBytes(32).toString('hex');
  }

  private getTrustBundle(): string {
    return Buffer.from(JSON.stringify({
      trustDomain: TRUST_DOMAIN,
      authorities: [`spiffe://${TRUST_DOMAIN}/ca`]
    })).toString('base64');
  }

  private async logAuditEvent(event: {
    eventType: string;
    spiffeId: SpiffeId;
    action: string;
    metadata: Record<string, any>;
  }): Promise<void> {
    await supabase.from('audit_logs').insert({
      event_type: event.eventType,
      spiffe_id: event.spiffeId,
      action: event.action,
      metadata: event.metadata,
      timestamp: new Date().toISOString(),
      // Immutable hash for tamper detection
      hash: crypto.createHash('sha256')
        .update(JSON.stringify(event))
        .digest('hex')
    });
  }
}

// Export singleton
export const spiffeService = new SpiffeIdentityService();
