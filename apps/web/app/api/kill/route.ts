/**
 * SPIFFE Kill API - Instant Agent Revocation Endpoint
 * 
 * This is the core kill switch mechanism using SPIFFE identity revocation.
 * Revoking a SPIFFE ID = Agent loses ALL access in <30 seconds
 * 
 * Endpoints:
 * POST /api/kill - Kill an agent immediately
 * POST /api/kill/emergency - Emergency kill all agents for a wallet
 * GET /api/kill/status - Check if agent is alive or killed
 */

import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

// Types
interface KillRequest {
  targetSpiffeId: string;
  reason: string;
  callerSpiffeId?: string;
  walletAddress?: string;
}

interface EmergencyKillRequest {
  walletAddress: string;
  reason: string;
}

interface KillResponse {
  success: boolean;
  killed: string[];
  killedAt: string;
  reason: string;
  effectiveLatency: string;
}

/**
 * POST /api/kill
 * Kill a single agent by revoking its SPIFFE identity
 */
export async function POST(req: NextRequest): Promise<NextResponse> {
  const startTime = Date.now();
  
  try {
    const body: KillRequest = await req.json();
    const { targetSpiffeId, reason, walletAddress } = body;

    // Validate required fields
    if (!targetSpiffeId || !reason) {
      return NextResponse.json(
        { error: 'targetSpiffeId and reason are required' },
        { status: 400 }
      );
    }

    // SECURITY FIX: walletAddress is REQUIRED for authorization
    if (!walletAddress) {
      return NextResponse.json(
        { error: 'walletAddress is required for authorization' },
        { status: 400 }
      );
    }

    // Validate wallet address format
    if (!/^0x[a-fA-F0-9]{40}$/.test(walletAddress)) {
      return NextResponse.json(
        { error: 'Invalid wallet address format' },
        { status: 400 }
      );
    }

    // Validate reason length
    if (reason.length < 3 || reason.length > 500) {
      return NextResponse.json(
        { error: 'Reason must be between 3 and 500 characters' },
        { status: 400 }
      );
    }

    // Verify caller owns this agent
    const { data: agent } = await supabase
      .from('agent_identities')
      .select('wallet_address, status')
      .eq('spiffe_id', targetSpiffeId)
      .single();

    if (!agent) {
      return NextResponse.json(
        { error: 'Agent not found' },
        { status: 404 }
      );
    }

    if (agent.wallet_address !== walletAddress) {
      // Log unauthorized attempt
      await logKillAttempt(targetSpiffeId, walletAddress, 'denied', reason);
      return NextResponse.json(
        { error: 'Unauthorized: You do not own this agent' },
        { status: 403 }
      );
    }

    if (agent.status === 'revoked') {
      return NextResponse.json(
        { error: 'Agent already killed' },
        { status: 409 }
      );
    }

    // EXECUTE KILL - Revoke SPIFFE identity
    const killedAt = new Date();
    
    const { error } = await supabase
      .from('agent_identities')
      .update({
        status: 'revoked',
        revoked_at: killedAt.toISOString(),
        revoked_by: walletAddress || 'system',
        revocation_reason: reason
      })
      .eq('spiffe_id', targetSpiffeId);

    if (error) {
      throw new Error(`Kill failed: ${error.message}`);
    }

    // Broadcast kill signal
    await broadcastKillSignal(targetSpiffeId, reason);

    // Log successful kill
    await logKillAttempt(targetSpiffeId, walletAddress || 'system', 'success', reason);

    const latencyMs = Date.now() - startTime;

    const response: KillResponse = {
      success: true,
      killed: [targetSpiffeId],
      killedAt: killedAt.toISOString(),
      reason,
      effectiveLatency: `${latencyMs}ms`
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Kill endpoint error:', error);
    return NextResponse.json(
      { error: 'Kill operation failed', details: String(error) },
      { status: 500 }
    );
  }
}

/**
 * Emergency Kill - Kill ALL agents for a wallet
 * Used when wallet is compromised or user wants to terminate everything
 */
export async function emergencyKill(req: NextRequest): Promise<NextResponse> {
  const startTime = Date.now();

  try {
    const body: EmergencyKillRequest = await req.json();
    const { walletAddress, reason } = body;

    if (!walletAddress || !reason) {
      return NextResponse.json(
        { error: 'walletAddress and reason are required' },
        { status: 400 }
      );
    }

    // Find all active agents for this wallet
    const { data: agents, error: fetchError } = await supabase
      .from('agent_identities')
      .select('spiffe_id')
      .eq('wallet_address', walletAddress)
      .eq('status', 'active');

    if (fetchError) {
      throw new Error(`Failed to fetch agents: ${fetchError.message}`);
    }

    if (!agents || agents.length === 0) {
      return NextResponse.json({
        success: true,
        killed: [],
        message: 'No active agents found'
      });
    }

    const killedAt = new Date();
    const killedIds: string[] = [];

    // Kill all agents
    for (const agent of agents) {
      const { error } = await supabase
        .from('agent_identities')
        .update({
          status: 'revoked',
          revoked_at: killedAt.toISOString(),
          revoked_by: 'emergency_kill',
          revocation_reason: `EMERGENCY: ${reason}`
        })
        .eq('spiffe_id', agent.spiffe_id);

      if (!error) {
        killedIds.push(agent.spiffe_id);
        await broadcastKillSignal(agent.spiffe_id, `EMERGENCY: ${reason}`);
      }
    }

    // Log emergency kill event
    await supabase.from('audit_logs').insert({
      event_type: 'emergency_kill',
      spiffe_id: `spiffe://killswitch.ai/wallet/${walletAddress}`,
      action: 'emergency_revoke',
      metadata: {
        walletAddress,
        reason,
        agentsKilled: killedIds.length,
        killedIds
      },
      timestamp: killedAt.toISOString()
    });

    const latencyMs = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      killed: killedIds,
      killedAt: killedAt.toISOString(),
      reason: `EMERGENCY: ${reason}`,
      effectiveLatency: `${latencyMs}ms`,
      totalKilled: killedIds.length
    });

  } catch (error) {
    console.error('Emergency kill error:', error);
    return NextResponse.json(
      { error: 'Emergency kill failed', details: String(error) },
      { status: 500 }
    );
  }
}

/**
 * Check agent status - Is it alive or killed?
 */
export async function getAgentStatus(spiffeId: string): Promise<{
  alive: boolean;
  status: string;
  lastSeen?: string;
  killedAt?: string;
  killedBy?: string;
  reason?: string;
}> {
  const { data: agent, error } = await supabase
    .from('agent_identities')
    .select('status, revoked_at, revoked_by, revocation_reason, updated_at')
    .eq('spiffe_id', spiffeId)
    .single();

  if (error || !agent) {
    return { alive: false, status: 'not_found' };
  }

  if (agent.status === 'revoked') {
    return {
      alive: false,
      status: 'killed',
      killedAt: agent.revoked_at,
      killedBy: agent.revoked_by,
      reason: agent.revocation_reason
    };
  }

  return {
    alive: true,
    status: agent.status,
    lastSeen: agent.updated_at
  };
}

/**
 * Broadcast kill signal to all services
 * Services subscribe to this table for real-time kill notifications
 */
async function broadcastKillSignal(spiffeId: string, reason: string): Promise<void> {
  await supabase.from('kill_signals').insert({
    spiffe_id: spiffeId,
    signal_type: 'immediate_termination',
    reason,
    broadcast_at: new Date().toISOString(),
    // TTL for cleanup - signals older than 1 hour can be purged
    expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString()
  });

  console.log(`🔴 KILL SIGNAL: ${spiffeId} - ${reason}`);
}

/**
 * Log kill attempts for audit trail
 */
async function logKillAttempt(
  targetSpiffeId: string,
  callerWallet: string,
  result: 'success' | 'denied' | 'error',
  reason: string
): Promise<void> {
  await supabase.from('audit_logs').insert({
    event_type: result === 'success' ? 'agent_killed' : 'kill_attempt_denied',
    spiffe_id: targetSpiffeId,
    action: result,
    metadata: {
      callerWallet,
      reason,
      result
    },
    timestamp: new Date().toISOString()
  });
}

/**
 * Database schema for SPIFFE integration
 * Run this in Supabase SQL editor
 */
export const SPIFFE_SCHEMA = `
-- Agent identities table (SPIFFE registry)
CREATE TABLE IF NOT EXISTS agent_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  spiffe_id TEXT UNIQUE NOT NULL,
  agent_id TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  agent_name TEXT,
  agent_type TEXT DEFAULT 'agent',
  issued_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired')),
  permissions TEXT[] DEFAULT ARRAY['api_call'],
  revoked_at TIMESTAMPTZ,
  revoked_by TEXT,
  revocation_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Kill signals table (real-time broadcast)
CREATE TABLE IF NOT EXISTS kill_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  spiffe_id TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  reason TEXT,
  broadcast_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

-- Enable real-time for kill signals
ALTER PUBLICATION supabase_realtime ADD TABLE kill_signals;

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_agent_identities_wallet ON agent_identities(wallet_address);
CREATE INDEX IF NOT EXISTS idx_agent_identities_status ON agent_identities(status);
CREATE INDEX IF NOT EXISTS idx_agent_identities_spiffe ON agent_identities(spiffe_id);
CREATE INDEX IF NOT EXISTS idx_kill_signals_spiffe ON kill_signals(spiffe_id);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agent_identities_updated_at
  BEFORE UPDATE ON agent_identities
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
`;
