import { Request, Response, Router, NextFunction } from 'express';
import fs from 'fs';
import path from 'path';
import { supabase, isSupabaseConfigured } from './db';

const router = Router();

// Audit log entry structure
interface AuditLogEntry {
  id: string;
  timestamp: number;
  userId: string | null;
  agentId: string | null;
  action: string;
  target: string;
  result: 'allowed' | 'blocked' | 'killed';
  riskScore: number;
  riskLevel: string;
  reasons: string[];
  ipAddress: string;
  userAgent: string;
  metadata: Record<string, unknown>;
  previousHash?: string;
  entryHash?: string;
}

// In-memory log store (fallback when Supabase is not configured)
const auditLogs: AuditLogEntry[] = [];
const MAX_LOGS = 10000; // Keep last 10k entries in memory

// Log file path
const LOG_DIR = process.env.LOG_DIR || './logs';
const LOG_FILE = path.join(LOG_DIR, 'audit.jsonl');

// Ensure log directory exists
function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

// Write log entry to file (append-only JSONL format)
function writeToFile(entry: AuditLogEntry) {
  try {
    ensureLogDir();
    fs.appendFileSync(LOG_FILE, JSON.stringify(entry) + '\n');
  } catch (err) {
    console.error('Failed to write audit log:', err);
  }
}

// Compute hash for audit chain integrity
function computeHash(entry: Omit<AuditLogEntry, 'entryHash'>): string {
  const crypto = require('crypto');
  const data = JSON.stringify({
    id: entry.id,
    timestamp: entry.timestamp,
    userId: entry.userId,
    agentId: entry.agentId,
    action: entry.action,
    target: entry.target,
    result: entry.result,
    previousHash: entry.previousHash
  });
  return crypto.createHash('sha256').update(data).digest('hex');
}

// Get the last audit log hash for chain integrity
async function getLastHash(): Promise<string | null> {
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('audit_logs')
      .select('entry_hash')
      .order('timestamp', { ascending: false })
      .limit(1)
      .single();
    
    if (error || !data) return null;
    return data.entry_hash;
  }
  
  if (auditLogs.length === 0) return null;
  return auditLogs[auditLogs.length - 1].entryHash || null;
}

// Create new audit log entry
export async function logAuditEvent(
  userId: string | null,
  agentId: string | null,
  action: string,
  target: string,
  result: 'allowed' | 'blocked' | 'killed',
  riskScore: number,
  riskLevel: string,
  reasons: string[],
  req?: Request,
  metadata?: Record<string, unknown>
): Promise<AuditLogEntry> {
  const id = 'LOG-' + Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
  const timestamp = Date.now();
  const previousHash = await getLastHash();
  
  const entry: AuditLogEntry = {
    id,
    timestamp,
    userId,
    agentId,
    action,
    target,
    result,
    riskScore,
    riskLevel,
    reasons,
    ipAddress: req?.ip || 'unknown',
    userAgent: req?.get('User-Agent') || 'unknown',
    metadata: metadata || {},
    previousHash: previousHash || undefined
  };
  
  // Compute entry hash for chain integrity
  entry.entryHash = computeHash(entry);

  // Add to in-memory store (always, as cache)
  auditLogs.push(entry);
  
  // Trim if too many
  if (auditLogs.length > MAX_LOGS) {
    auditLogs.shift();
  }

  // Write to file (always, as backup)
  writeToFile(entry);

  // Insert into Supabase if configured
  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('audit_logs')
      .insert({
        id: entry.id,
        timestamp: entry.timestamp,
        user_id: entry.userId,
        agent_id: entry.agentId,
        action: entry.action,
        target: entry.target,
        result: entry.result,
        risk_score: entry.riskScore,
        risk_level: entry.riskLevel,
        reasons: entry.reasons,
        ip_address: entry.ipAddress,
        user_agent: entry.userAgent,
        metadata: entry.metadata,
        previous_hash: entry.previousHash,
        entry_hash: entry.entryHash,
        created_at: timestamp
      });
    
    if (error) {
      console.error('Failed to insert audit log into Supabase:', error);
    }
  }

  return entry;
}

// Middleware to log all fence-related requests
export function auditMiddleware(req: Request, res: Response, next: NextFunction) {
  const originalJson = res.json.bind(res);
  
  res.json = function(body: any) {
    // Log fence assessment results
    if (req.path.includes('/runtime/assess') && body) {
      logAuditEvent(
        (req as any).user?.id || null,
        body.agentId || req.body?.agentId || null,
        req.body?.action || 'unknown',
        req.body?.context?.target || 'unknown',
        body.allowed ? 'allowed' : 'blocked',
        body.riskScore || 0,
        body.riskLevel || 'unknown',
        body.reasons || [],
        req
      );
    }
    
    // Log kill switch activations
    if (req.path.includes('/runtime/kill') && body?.success) {
      logAuditEvent(
        (req as any).user?.id || null,
        req.body?.agentId || 'all',
        'kill_switch',
        'system',
        'killed',
        100,
        'critical',
        [req.body?.reason || 'Manual kill'],
        req
      );
    }

    return originalJson(body);
  };

  next();
}

// ============================================
// Audit Log API Endpoints
// ============================================

// Get recent audit logs
router.get('/api/audit-logs', async (req: Request, res: Response) => {
  const { limit = 100, offset = 0, agentId, action, result } = req.query;
  
  const limitNum = Number(limit);
  const offsetNum = Number(offset);
  
  if (isSupabaseConfigured()) {
    let query = supabase
      .from('audit_logs')
      .select('*', { count: 'exact' })
      .order('timestamp', { ascending: false })
      .range(offsetNum, offsetNum + limitNum - 1);
    
    if (agentId) {
      query = query.eq('agent_id', agentId);
    }
    if (action) {
      query = query.eq('action', action);
    }
    if (result) {
      query = query.eq('result', result);
    }
    
    const { data, error, count } = await query;
    
    if (error) {
      console.error('Failed to fetch audit logs from Supabase:', error);
      return res.status(500).json({ error: 'Failed to fetch audit logs' });
    }
    
    const logs = (data || []).map(row => ({
      id: row.id,
      timestamp: row.timestamp,
      userId: row.user_id,
      agentId: row.agent_id,
      action: row.action,
      target: row.target,
      result: row.result,
      riskScore: row.risk_score,
      riskLevel: row.risk_level,
      reasons: row.reasons,
      ipAddress: row.ip_address,
      userAgent: row.user_agent,
      metadata: row.metadata,
      previousHash: row.previous_hash,
      entryHash: row.entry_hash
    }));
    
    return res.json({
      total: count || 0,
      offset: offsetNum,
      limit: limitNum,
      logs
    });
  }
  
  // Fallback to in-memory
  let filtered = [...auditLogs];
  
  // Apply filters
  if (agentId) {
    filtered = filtered.filter(log => log.agentId === agentId);
  }
  if (action) {
    filtered = filtered.filter(log => log.action === action);
  }
  if (result) {
    filtered = filtered.filter(log => log.result === result);
  }
  
  // Sort by timestamp descending (most recent first)
  filtered.sort((a, b) => b.timestamp - a.timestamp);
  
  // Paginate
  const start = offsetNum;
  const end = start + limitNum;
  const paginated = filtered.slice(start, end);
  
  res.json({
    total: filtered.length,
    offset: start,
    limit: limitNum,
    logs: paginated
  });
});

// Get audit log by ID
router.get('/api/audit-logs/:id', async (req: Request, res: Response) => {
  const logId = req.params.id;
  
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('audit_logs')
      .select('*')
      .eq('id', logId)
      .single();
    
    if (error || !data) {
      return res.status(404).json({ error: 'Log entry not found' });
    }
    
    return res.json({
      id: data.id,
      timestamp: data.timestamp,
      userId: data.user_id,
      agentId: data.agent_id,
      action: data.action,
      target: data.target,
      result: data.result,
      riskScore: data.risk_score,
      riskLevel: data.risk_level,
      reasons: data.reasons,
      ipAddress: data.ip_address,
      userAgent: data.user_agent,
      metadata: data.metadata,
      previousHash: data.previous_hash,
      entryHash: data.entry_hash
    });
  }
  
  const log = auditLogs.find(l => l.id === logId);
  
  if (!log) {
    return res.status(404).json({ error: 'Log entry not found' });
  }
  
  res.json(log);
});

// Get audit log statistics
router.get('/api/audit-logs/stats', async (req: Request, res: Response) => {
  const { since } = req.query;
  const sinceTs = since ? Number(since) : Date.now() - 24 * 60 * 60 * 1000; // Last 24 hours
  
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('audit_logs')
      .select('*')
      .gte('timestamp', sinceTs);
    
    if (error) {
      console.error('Failed to fetch audit stats from Supabase:', error);
      return res.status(500).json({ error: 'Failed to fetch audit stats' });
    }
    
    const recentLogs = data || [];
    
    const stats = {
      totalEvents: recentLogs.length,
      allowed: recentLogs.filter((l: any) => l.result === 'allowed').length,
      blocked: recentLogs.filter((l: any) => l.result === 'blocked').length,
      killed: recentLogs.filter((l: any) => l.result === 'killed').length,
      avgRiskScore: recentLogs.length > 0 
        ? Math.round(recentLogs.reduce((sum: number, l: any) => sum + l.risk_score, 0) / recentLogs.length)
        : 0,
      topBlockedActions: getTopItems(recentLogs.filter((l: any) => l.result === 'blocked'), 'action', 5),
      topBlockedTargets: getTopItems(recentLogs.filter((l: any) => l.result === 'blocked'), 'target', 5),
      activeAgents: [...new Set(recentLogs.map((l: any) => l.agent_id).filter(Boolean))].length,
      period: {
        from: sinceTs,
        to: Date.now()
      }
    };
    
    return res.json(stats);
  }
  
  // Fallback to in-memory
  const recentLogs = auditLogs.filter(log => log.timestamp >= sinceTs);
  
  const stats = {
    totalEvents: recentLogs.length,
    allowed: recentLogs.filter(l => l.result === 'allowed').length,
    blocked: recentLogs.filter(l => l.result === 'blocked').length,
    killed: recentLogs.filter(l => l.result === 'killed').length,
    avgRiskScore: recentLogs.length > 0 
      ? Math.round(recentLogs.reduce((sum, l) => sum + l.riskScore, 0) / recentLogs.length)
      : 0,
    topBlockedActions: getTopItems(recentLogs.filter(l => l.result === 'blocked'), 'action', 5),
    topBlockedTargets: getTopItems(recentLogs.filter(l => l.result === 'blocked'), 'target', 5),
    activeAgents: [...new Set(recentLogs.map(l => l.agentId).filter(Boolean))].length,
    period: {
      from: sinceTs,
      to: Date.now()
    }
  };
  
  res.json(stats);
});

// Helper: Get top N items by frequency
function getTopItems(logs: any[], field: string, n: number): { value: string; count: number }[] {
  const counts: Record<string, number> = {};
  
  logs.forEach(log => {
    const value = String(log[field]);
    counts[value] = (counts[value] || 0) + 1;
  });
  
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([value, count]) => ({ value, count }));
}

// Export logs as CSV
router.get('/api/audit-logs/export/csv', async (req: Request, res: Response) => {
  const { since, until } = req.query;
  const sinceTs = since ? Number(since) : 0;
  const untilTs = until ? Number(until) : Date.now();
  
  let filtered: AuditLogEntry[] = [];
  
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('audit_logs')
      .select('*')
      .gte('timestamp', sinceTs)
      .lte('timestamp', untilTs);
    
    if (error) {
      console.error('Failed to export audit logs from Supabase:', error);
      return res.status(500).json({ error: 'Failed to export audit logs' });
    }
    
    filtered = (data || []).map(row => ({
      id: row.id,
      timestamp: row.timestamp,
      userId: row.user_id,
      agentId: row.agent_id,
      action: row.action,
      target: row.target,
      result: row.result,
      riskScore: row.risk_score,
      riskLevel: row.risk_level,
      reasons: row.reasons,
      ipAddress: row.ip_address,
      userAgent: row.user_agent,
      metadata: row.metadata
    }));
  } else {
    filtered = auditLogs.filter(log => 
      log.timestamp >= sinceTs && log.timestamp <= untilTs
    );
  }
  
  const headers = ['id', 'timestamp', 'userId', 'agentId', 'action', 'target', 'result', 'riskScore', 'riskLevel', 'reasons'];
  const csvRows = [
    headers.join(','),
    ...filtered.map(log => [
      log.id,
      new Date(log.timestamp).toISOString(),
      log.userId || '',
      log.agentId || '',
      log.action,
      log.target,
      log.result,
      log.riskScore,
      log.riskLevel,
      `"${log.reasons.join('; ')}"`
    ].join(','))
  ];
  
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename=audit-logs.csv');
  res.send(csvRows.join('\n'));
});

// Export logs as JSON
router.get('/api/audit-logs/export/json', async (req: Request, res: Response) => {
  const { since, until } = req.query;
  const sinceTs = since ? Number(since) : 0;
  const untilTs = until ? Number(until) : Date.now();
  
  let filtered: AuditLogEntry[] = [];
  
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('audit_logs')
      .select('*')
      .gte('timestamp', sinceTs)
      .lte('timestamp', untilTs);
    
    if (error) {
      console.error('Failed to export audit logs from Supabase:', error);
      return res.status(500).json({ error: 'Failed to export audit logs' });
    }
    
    filtered = (data || []).map(row => ({
      id: row.id,
      timestamp: row.timestamp,
      userId: row.user_id,
      agentId: row.agent_id,
      action: row.action,
      target: row.target,
      result: row.result,
      riskScore: row.risk_score,
      riskLevel: row.risk_level,
      reasons: row.reasons,
      ipAddress: row.ip_address,
      userAgent: row.user_agent,
      metadata: row.metadata,
      previousHash: row.previous_hash,
      entryHash: row.entry_hash
    }));
  } else {
    filtered = auditLogs.filter(log => 
      log.timestamp >= sinceTs && log.timestamp <= untilTs
    );
  }
  
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Content-Disposition', 'attachment; filename=audit-logs.json');
  res.json({ exported: Date.now(), logs: filtered });
});

export default router;
