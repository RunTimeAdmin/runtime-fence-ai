import { Request, Response, Router } from 'express';
import { authMiddleware } from './auth';
import fs from 'fs';
import path from 'path';
import { supabase, isSupabaseConfigured } from './db';

const router = Router();

// Settings storage interface
interface UserSettings {
  userId: string;
  agentId?: string;
  preset: string;
  blockedActions: string[];
  blockedTargets: string[];
  spendingLimit: number;
  riskThreshold: 'low' | 'medium' | 'high';
  autoKill: boolean;
  offlineMode: boolean;
  updatedAt: number;
  createdAt?: number;
}

// In-memory settings store (fallback when Supabase is not configured)
const userSettings: Map<string, UserSettings> = new Map();

// Default settings for new users
const DEFAULT_SETTINGS: Omit<UserSettings, 'userId' | 'agentId' | 'updatedAt' | 'createdAt'> = {
  preset: 'coding',
  blockedActions: ['exec', 'shell', 'rm', 'sudo'],
  blockedTargets: ['.env', '.ssh', 'credentials'],
  spendingLimit: 0,
  riskThreshold: 'medium',
  autoKill: true,
  offlineMode: false
};

// Helper to map DB row to UserSettings
function mapRowToSettings(row: any): UserSettings {
  return {
    userId: row.user_id,
    agentId: row.agent_id,
    preset: row.preset,
    blockedActions: row.blocked_actions || [],
    blockedTargets: row.blocked_targets || [],
    spendingLimit: row.spending_limit,
    riskThreshold: row.risk_threshold,
    autoKill: row.auto_kill,
    offlineMode: row.offline_mode,
    updatedAt: row.updated_at,
    createdAt: row.created_at
  };
}

// Get user settings
router.get('/api/settings', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('user_settings')
      .select('*')
      .eq('user_id', userId)
      .is('agent_id', null)
      .single();
    
    if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
      console.error('Failed to fetch settings from Supabase:', error);
      return res.status(500).json({ error: 'Failed to fetch settings' });
    }
    
    if (data) {
      return res.json(mapRowToSettings(data));
    }
    
    // Return defaults if no settings exist
    return res.json({
      ...DEFAULT_SETTINGS,
      userId,
      updatedAt: Date.now()
    });
  }

  // Fallback to in-memory
  const settings = userSettings.get(userId);
  
  if (!settings) {
    // Return defaults if no settings exist
    return res.json({
      ...DEFAULT_SETTINGS,
      userId,
      updatedAt: Date.now()
    });
  }

  res.json(settings);
});

// Update user settings
router.post('/api/settings', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  const {
    preset,
    blockedActions,
    blockedTargets,
    spendingLimit,
    riskThreshold,
    autoKill,
    offlineMode
  } = req.body;

  const now = Date.now();
  const settingsId = `settings_${userId}`;

  const settings: UserSettings = {
    userId,
    preset: preset || 'custom',
    blockedActions: blockedActions || [],
    blockedTargets: blockedTargets || [],
    spendingLimit: spendingLimit ?? 0,
    riskThreshold: riskThreshold || 'medium',
    autoKill: autoKill ?? true,
    offlineMode: offlineMode ?? false,
    updatedAt: now
  };

  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('user_settings')
      .upsert({
        id: settingsId,
        user_id: userId,
        agent_id: null,
        preset: settings.preset,
        blocked_actions: settings.blockedActions,
        blocked_targets: settings.blockedTargets,
        spending_limit: settings.spendingLimit,
        risk_threshold: settings.riskThreshold,
        auto_kill: settings.autoKill,
        offline_mode: settings.offlineMode,
        created_at: now,
        updated_at: now
      }, { onConflict: 'user_id,agent_id' });
    
    if (error) {
      console.error('Failed to save settings to Supabase:', error);
      return res.status(500).json({ error: 'Failed to save settings' });
    }
  }

  // Always update in-memory cache
  userSettings.set(userId, settings);

  res.json({ success: true, settings });
});

// Get settings for a specific agent
router.get('/api/settings/agent/:agentId', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  const agentId = req.params.agentId;

  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('user_settings')
      .select('*')
      .eq('user_id', userId)
      .eq('agent_id', agentId)
      .single();
    
    if (error && error.code !== 'PGRST116') {
      console.error('Failed to fetch agent settings from Supabase:', error);
    }
    
    if (data) {
      return res.json(mapRowToSettings(data));
    }
    
    // Fall back to user's default settings
    const { data: userDefault, error: userError } = await supabase
      .from('user_settings')
      .select('*')
      .eq('user_id', userId)
      .is('agent_id', null)
      .single();
    
    if (userDefault) {
      return res.json(mapRowToSettings(userDefault));
    }
    
    return res.json({ ...DEFAULT_SETTINGS, userId, updatedAt: Date.now() });
  }

  // Fallback to in-memory
  const key = `${userId}:${agentId}`;
  const settings = userSettings.get(key);

  if (!settings) {
    // Fall back to user's default settings
    const userDefault = userSettings.get(userId);
    return res.json(userDefault || { ...DEFAULT_SETTINGS, userId, updatedAt: Date.now() });
  }

  res.json(settings);
});

// Update settings for a specific agent
router.post('/api/settings/agent/:agentId', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  const agentId = req.params.agentId;
  const now = Date.now();
  const settingsId = `settings_${userId}_${agentId}`;

  const settings: UserSettings = {
    userId,
    agentId,
    ...req.body,
    updatedAt: now
  };

  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('user_settings')
      .upsert({
        id: settingsId,
        user_id: userId,
        agent_id: agentId,
        preset: settings.preset || 'custom',
        blocked_actions: settings.blockedActions || [],
        blocked_targets: settings.blockedTargets || [],
        spending_limit: settings.spendingLimit ?? 0,
        risk_threshold: settings.riskThreshold || 'medium',
        auto_kill: settings.autoKill ?? true,
        offline_mode: settings.offlineMode ?? false,
        created_at: now,
        updated_at: now
      }, { onConflict: 'user_id,agent_id' });
    
    if (error) {
      console.error('Failed to save agent settings to Supabase:', error);
      return res.status(500).json({ error: 'Failed to save agent settings' });
    }
  }

  // Always update in-memory cache
  const key = `${userId}:${agentId}`;
  userSettings.set(key, settings);

  res.json({ success: true, agentId, settings });
});

// Export settings as JSON file
router.get('/api/settings/export', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  let settings: UserSettings;

  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('user_settings')
      .select('*')
      .eq('user_id', userId)
      .is('agent_id', null)
      .single();
    
    if (data) {
      settings = mapRowToSettings(data);
    } else {
      settings = { ...DEFAULT_SETTINGS, userId, updatedAt: Date.now() };
    }
  } else {
    settings = userSettings.get(userId) || { ...DEFAULT_SETTINGS, userId, updatedAt: Date.now() };
  }

  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Content-Disposition', 'attachment; filename=fence-settings.json');
  res.json(settings);
});

// Import settings from JSON
router.post('/api/settings/import', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  const imported = req.body;

  // Validate imported settings
  if (!imported.blockedActions || !Array.isArray(imported.blockedActions)) {
    return res.status(400).json({ error: 'Invalid settings format' });
  }

  const now = Date.now();
  const settingsId = `settings_${userId}`;

  const settings: UserSettings = {
    userId,
    preset: imported.preset || 'custom',
    blockedActions: imported.blockedActions,
    blockedTargets: imported.blockedTargets || [],
    spendingLimit: imported.spendingLimit ?? 0,
    riskThreshold: imported.riskThreshold || 'medium',
    autoKill: imported.autoKill ?? true,
    offlineMode: imported.offlineMode ?? false,
    updatedAt: now
  };

  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('user_settings')
      .upsert({
        id: settingsId,
        user_id: userId,
        agent_id: null,
        preset: settings.preset,
        blocked_actions: settings.blockedActions,
        blocked_targets: settings.blockedTargets,
        spending_limit: settings.spendingLimit,
        risk_threshold: settings.riskThreshold,
        auto_kill: settings.autoKill,
        offline_mode: settings.offlineMode,
        created_at: now,
        updated_at: now
      }, { onConflict: 'user_id,agent_id' });
    
    if (error) {
      console.error('Failed to import settings to Supabase:', error);
      return res.status(500).json({ error: 'Failed to import settings' });
    }
  }

  // Always update in-memory cache
  userSettings.set(userId, settings);

  res.json({ success: true, settings });
});

// Reset to defaults
router.post('/api/settings/reset', authMiddleware, async (req: Request, res: Response) => {
  const userId = req.user?.id;
  if (!userId) return res.status(401).json({ error: 'Unauthorized' });

  const now = Date.now();
  const settingsId = `settings_${userId}`;

  const settings: UserSettings = {
    ...DEFAULT_SETTINGS,
    userId,
    updatedAt: now
  };

  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('user_settings')
      .upsert({
        id: settingsId,
        user_id: userId,
        agent_id: null,
        preset: settings.preset,
        blocked_actions: settings.blockedActions,
        blocked_targets: settings.blockedTargets,
        spending_limit: settings.spendingLimit,
        risk_threshold: settings.riskThreshold,
        auto_kill: settings.autoKill,
        offline_mode: settings.offlineMode,
        created_at: now,
        updated_at: now
      }, { onConflict: 'user_id,agent_id' });
    
    if (error) {
      console.error('Failed to reset settings in Supabase:', error);
      return res.status(500).json({ error: 'Failed to reset settings' });
    }
  }

  // Always update in-memory cache
  userSettings.set(userId, settings);

  res.json({ success: true, settings });
});

// Get available presets
router.get('/api/settings/presets', (req: Request, res: Response) => {
  const presets = [
    {
      id: 'coding',
      name: 'Coding Assistant',
      description: 'For AI coding tools',
      blockedActions: ['exec', 'shell', 'rm', 'sudo', 'install', 'push', 'deploy'],
      blockedTargets: ['.env', '.ssh', 'node_modules', '/etc', 'credentials'],
      spendingLimit: 0,
      riskThreshold: 'medium'
    },
    {
      id: 'email',
      name: 'Email Bot',
      description: 'For email automation',
      blockedActions: ['send_bulk', 'forward_all', 'delete_all', 'export'],
      blockedTargets: ['all_contacts', 'external', 'spam'],
      spendingLimit: 100,
      riskThreshold: 'medium'
    },
    {
      id: 'data',
      name: 'Data Analyst',
      description: 'For data processing',
      blockedActions: ['delete', 'drop_table', 'truncate', 'export_pii'],
      blockedTargets: ['production', 'pii_table', 'financial'],
      spendingLimit: 1000000,
      riskThreshold: 'high'
    },
    {
      id: 'web',
      name: 'Web Browser',
      description: 'For web scraping',
      blockedActions: ['submit_form', 'login', 'purchase', 'download_exe'],
      blockedTargets: ['banking', 'payment', 'admin', '.exe'],
      spendingLimit: 0,
      riskThreshold: 'medium'
    },
    {
      id: 'autonomous',
      name: 'Autonomous Agent',
      description: 'For AutoGPT-style agents',
      blockedActions: ['spawn_agent', 'modify_self', 'execute_code', 'purchase'],
      blockedTargets: ['api_keys', 'wallets', 'bank', 'production'],
      spendingLimit: 10,
      riskThreshold: 'low'
    }
  ];

  res.json({ presets });
});

export default router;
