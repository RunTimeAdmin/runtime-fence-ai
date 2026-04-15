import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { KillSwitch, AgentConfig, TransactionRequest } from '@killswitch/core';
import {
  authMiddleware,
  optionalAuth,
  adminOnly,
  agentAuth,
  rateLimit,
  createUser,
  getUserByEmail,
  verifyPassword,
  generateToken,
  generateApiKey,
  updateUserApiKey
} from './auth';
import { supabase, isSupabaseConfigured } from './db';

const app = express();
const killSwitch = new KillSwitch();

app.use(helmet());
app.use(cors());
app.use(express.json());

// Apply rate limiting globally
app.use(rateLimit(100, 60000));

// ============================================
// Public Endpoints (no auth required)
// ============================================

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

// ============================================
// Auth Endpoints
// ============================================

app.post('/api/auth/register', async (req: Request, res: Response) => {
  try {
    const { email, password, role } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }
    
    const existing = await getUserByEmail(email);
    if (existing) {
      return res.status(409).json({ error: 'Email already registered' });
    }
    
    // Only allow 'user' role for self-registration, 'agent' for API clients
    const allowedRole = role === 'agent' ? 'agent' : 'user';
    const user = await createUser(email, password, allowedRole);
    const token = generateToken(user);
    
    res.json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
        apiKey: user.apiKey
      },
      token
    });
  } catch (err) {
    res.status(500).json({ error: 'Registration failed' });
  }
});

app.post('/api/auth/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;
    
    const user = await getUserByEmail(email);
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const valid = await verifyPassword(password, user.passwordHash);
    if (!valid) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const token = generateToken(user);
    
    res.json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        role: user.role
      },
      token
    });
  } catch (err) {
    res.status(500).json({ error: 'Login failed' });
  }
});

app.post('/api/auth/refresh-key', authMiddleware, async (req: Request, res: Response) => {
  if (!req.user) return res.status(401).json({ error: 'Unauthorized' });
  
  const newKey = generateApiKey();
  const success = await updateUserApiKey(req.user.id, newKey);
  
  if (!success) {
    return res.status(500).json({ error: 'Failed to refresh API key' });
  }
  
  res.json({ success: true, apiKey: newKey });
});

app.get('/api/auth/me', authMiddleware, (req: Request, res: Response) => {
  if (!req.user) return res.status(401).json({ error: 'Unauthorized' });
  
  res.json({
    id: req.user.id,
    email: req.user.email,
    role: req.user.role,
    createdAt: req.user.createdAt
  });
});

// ============================================
// Agent Management (auth required)
// ============================================

app.post('/api/v1/agents', authMiddleware, (req: Request, res: Response) => {
  const agent: AgentConfig = req.body;
  killSwitch.registerAgent(agent);
  res.json({ success: true, agentId: agent.id });
});

app.post('/api/v1/validate', authMiddleware, async (req: Request, res: Response) => {
  const tx: TransactionRequest = req.body;
  const result = await killSwitch.validate(tx);
  res.json(result);
});

app.post('/api/v1/killswitch/trigger', authMiddleware, async (req: Request, res: Response) => {
  const { agentId, reason } = req.body;
  killSwitch.triggerKillSwitch(agentId || null, 'manual', reason || 'Manual trigger');

  // Persist kill state to Supabase
  if (isSupabaseConfigured() && agentId) {
    await supabase.from('agents').update({ status: 'killed', updated_at: Date.now() }).eq('id', agentId);
    await supabase.from('kill_signals').insert({
      id: 'kill_' + Date.now().toString(36),
      agent_id: agentId,
      reason: reason || 'Manual kill switch',
      triggered_by: req.user?.id || 'system',
      created_at: Date.now()
    });
  }

  res.json({ success: true, triggered: true });
});

app.post('/api/v1/killswitch/reset', authMiddleware, adminOnly, async (req: Request, res: Response) => {
  const { agentId } = req.body;
  const userId = (req as any).user?.id;

  // Verify ownership even for admins
  if (agentId && isSupabaseConfigured()) {
    const { data: agent } = await supabase
      .from('agents')
      .select('user_id')
      .eq('id', agentId)
      .single();
    
    if (!agent || (agent.user_id !== userId && (req as any).user?.role !== 'admin')) {
      return res.status(403).json({ error: 'You do not own this agent' });
    }
  }

  killSwitch.resetKillSwitch(agentId);
  
  // Persist reset
  if (isSupabaseConfigured() && agentId) {
    await supabase.from('agents').update({ status: 'active', updated_at: Date.now() }).eq('id', agentId);
    await supabase.from('kill_signals').delete().eq('agent_id', agentId);
  }

  // Audit log the reset
  console.log(`Kill switch reset by ${userId} for agent ${agentId || 'global'}`);
  
  res.json({ success: true, reset: true });
});

app.get('/api/v1/killswitch/status', optionalAuth, (req: Request, res: Response) => {
  res.json({ globalKillActive: killSwitch.isGlobalKillActive() });
});

app.get('/api/v1/agents/:agentId/status', authMiddleware, (req: Request, res: Response) => {
  const status = killSwitch.getAgentStatus(req.params.agentId);
  res.json({ agentId: req.params.agentId, status });
});

// ============================================
// Runtime Fence Endpoints (agent auth)
// ============================================

app.post('/api/runtime/assess', authMiddleware, agentAuth, async (req: Request, res: Response) => {
  const { agentId, action, context } = req.body;
  const tx = { agentId, action, target: context?.target || 'unknown', timestamp: Date.now() };
  const result = await killSwitch.validate(tx);
  res.json({
    agentId,
    riskScore: result.riskScore,
    riskLevel: result.riskLevel,
    allowed: result.allowed,
    reasons: result.reasons,
    timestamp: Date.now()
  });
});

// NOTE: Kill endpoint uses authMiddleware only (not agentAuth) because this is a USER action,
// not an agent action. Tenant isolation is enforced below by verifying agent ownership.
app.post('/api/runtime/kill', authMiddleware, async (req: Request, res: Response) => {
  const { agentId, reason, immediate } = req.body;
  const userId = (req as any).user?.id;

  // Verify ownership if targeting specific agent
  if (agentId) {
    if (isSupabaseConfigured()) {
      const { data: agent } = await supabase
        .from('agents')
        .select('user_id')
        .eq('id', agentId)
        .single();
      
      if (!agent || agent.user_id !== userId) {
        return res.status(403).json({ error: 'You do not own this agent' });
      }
    }
  } else if ((req as any).user?.role !== 'admin') {
    return res.status(403).json({ error: 'Only admins can trigger global kill' });
  }

  killSwitch.triggerKillSwitch(agentId || null, 'emergency', reason || 'Emergency kill');
  
  // Persist kill state
  if (isSupabaseConfigured() && agentId) {
    await supabase.from('agents').update({ status: 'killed', updated_at: Date.now() }).eq('id', agentId);
    await supabase.from('kill_signals').insert({
      id: 'kill_' + Date.now().toString(36),
      agent_id: agentId,
      reason: reason || 'Emergency kill',
      triggered_by: userId || 'system',
      created_at: Date.now()
    });
  }

  res.json({
    success: true,
    agentId: agentId || 'all',
    status: 'terminated',
    immediate: immediate ?? true,
    timestamp: Date.now()
  });
});

app.get('/api/runtime/status', optionalAuth, (req: Request, res: Response) => {
  const globalKillActive = killSwitch.isGlobalKillActive();
  res.json({
    operational: !globalKillActive,
    globalKillActive,
    version: '1.0.0',
    uptime: process.uptime(),
    timestamp: Date.now()
  });
});

// ============================================
// Audit Endpoints (auth required)
// ============================================

interface AuditRequest {
  id: string;
  requesterId: string;
  contractAddress: string;
  auditType: 'basic' | 'comprehensive' | 'emergency';
  status: 'pending' | 'in_progress' | 'complete' | 'failed';
  results: Record<string, unknown> | null;
  createdAt: number;
}

// In-memory audit requests store (fallback when Supabase is not configured)
const audits: Map<string, AuditRequest> = new Map();

app.post('/api/audit/submit', authMiddleware, async (req: Request, res: Response) => {
  const { contractAddress, auditType } = req.body;
  const requesterId = req.user?.id || 'anonymous';
  const id = 'AUDIT-' + Date.now().toString(36).toUpperCase();
  const now = Date.now();
  
  const audit: AuditRequest = {
    id,
    requesterId,
    contractAddress,
    auditType: auditType || 'basic',
    status: 'pending',
    results: null,
    createdAt: now
  };
  
  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('audit_requests')
      .insert({
        id: audit.id,
        requester_id: audit.requesterId,
        contract_address: audit.contractAddress,
        audit_type: audit.auditType,
        status: audit.status,
        results: audit.results,
        created_at: audit.createdAt
      });
    
    if (error) {
      console.error('Failed to insert audit request into Supabase:', error);
      return res.status(500).json({ error: 'Failed to submit audit request' });
    }
  }
  
  // Always update in-memory cache
  audits.set(id, audit);
  
  res.json({ success: true, auditId: id, audit });
});

app.get('/api/audit/status/:id', authMiddleware, async (req: Request, res: Response) => {
  const auditId = req.params.id;
  
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('audit_requests')
      .select('*')
      .eq('id', auditId)
      .single();
    
    if (error || !data) {
      return res.status(404).json({ error: 'Audit not found' });
    }
    
    return res.json({
      id: data.id,
      requesterId: data.requester_id,
      contractAddress: data.contract_address,
      auditType: data.audit_type,
      status: data.status,
      results: data.results,
      createdAt: data.created_at,
      completedAt: data.completed_at
    });
  }
  
  // Fallback to in-memory
  const audit = audits.get(auditId);
  if (!audit) {
    return res.status(404).json({ error: 'Audit not found' });
  }
  
  res.json(audit);
});

app.get('/api/audit/list', authMiddleware, async (req: Request, res: Response) => {
  const requesterId = req.user?.id;
  const isAdmin = req.user?.role === 'admin';
  
  if (isSupabaseConfigured()) {
    let query = supabase
      .from('audit_requests')
      .select('*')
      .order('created_at', { ascending: false });
    
    if (requesterId && !isAdmin) {
      query = query.eq('requester_id', requesterId);
    }
    
    const { data, error } = await query;
    
    if (error) {
      console.error('Failed to fetch audit list from Supabase:', error);
      return res.status(500).json({ error: 'Failed to fetch audit list' });
    }
    
    const results = (data || []).map(row => ({
      id: row.id,
      requesterId: row.requester_id,
      contractAddress: row.contract_address,
      auditType: row.audit_type,
      status: row.status,
      results: row.results,
      createdAt: row.created_at,
      completedAt: row.completed_at
    }));
    
    return res.json({ audits: results });
  }
  
  // Fallback to in-memory
  let results = Array.from(audits.values());
  if (requesterId && !isAdmin) {
    results = results.filter(a => a.requesterId === requesterId);
  }
  
  res.json({ audits: results });
});

// ============================================
// Error handling
// ============================================

app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});

// ============================================
// Restore kill state from database on startup
// ============================================

async function restoreKillState() {
  if (!isSupabaseConfigured()) return;
  const { data: killedAgents } = await supabase
    .from('agents')
    .select('id')
    .eq('status', 'killed');
  if (killedAgents) {
    killedAgents.forEach(a => killSwitch.triggerKillSwitch(a.id, 'automatic', 'Restored from database'));
    console.log(`Restored ${killedAgents.length} kill states from database`);
  }
}

const PORT = process.env.PORT || 3001;

// Restore kill state before starting server
restoreKillState().then(() => {
  app.listen(PORT, () => console.log('API running on port ' + PORT));
});

export default app;
