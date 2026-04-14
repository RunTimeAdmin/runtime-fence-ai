import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { supabase, isSupabaseConfigured } from './db';

const JWT_SECRET = process.env.JWT_SECRET || 'killswitch-dev-secret-change-in-production';
const JWT_EXPIRES = '24h';

// In-memory user store (fallback when Supabase is not configured)
interface User {
  id: string;
  email: string;
  passwordHash: string;
  apiKey: string;
  role: 'user' | 'admin' | 'agent';
  tier?: string;
  createdAt: number;
}

const users: Map<string, User> = new Map();
const apiKeys: Map<string, User> = new Map();

// Extend Express Request type
declare global {
  namespace Express {
    interface Request {
      user?: User;
    }
  }
}

// ============================================
// Password hashing
// ============================================

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

// ============================================
// JWT Token handling
// ============================================

export function generateToken(user: User): string {
  return jwt.sign(
    { 
      id: user.id, 
      email: user.email, 
      role: user.role 
    },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRES }
  );
}

export function verifyToken(token: string): { id: string; email: string; role: string } | null {
  try {
    return jwt.verify(token, JWT_SECRET) as { id: string; email: string; role: string };
  } catch {
    return null;
  }
}

// ============================================
// API Key generation
// ============================================

export function generateApiKey(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let key = 'ks_';
  for (let i = 0; i < 32; i++) {
    key += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return key;
}

// ============================================
// User management
// ============================================

export async function createUser(email: string, password: string, role: 'user' | 'admin' | 'agent' = 'user'): Promise<User> {
  const id = 'user_' + Date.now().toString(36);
  const passwordHash = await hashPassword(password);
  const apiKey = generateApiKey();
  const now = Date.now();
  
  const user: User = {
    id,
    email,
    passwordHash,
    apiKey,
    role,
    createdAt: now
  };
  
  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('users')
      .insert({
        id,
        email,
        password_hash: passwordHash,
        api_key: apiKey,
        role,
        tier: 'basic',
        created_at: now
      });
    
    if (error) {
      console.error('Failed to create user in Supabase:', error);
      throw new Error('Failed to create user');
    }
  }
  
  // Always update in-memory cache
  users.set(id, user);
  users.set(email, user);
  apiKeys.set(apiKey, user);
  
  return user;
}

export async function getUserById(id: string): Promise<User | undefined> {
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('users')
      .select('*')
      .eq('id', id)
      .single();
    
    if (error || !data) return undefined;
    
    return {
      id: data.id,
      email: data.email,
      passwordHash: data.password_hash,
      apiKey: data.api_key,
      role: data.role,
      tier: data.tier,
      createdAt: data.created_at
    };
  }
  
  return users.get(id);
}

export async function getUserByEmail(email: string): Promise<User | undefined> {
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('users')
      .select('*')
      .eq('email', email)
      .single();
    
    if (error || !data) return undefined;
    
    return {
      id: data.id,
      email: data.email,
      passwordHash: data.password_hash,
      apiKey: data.api_key,
      role: data.role,
      tier: data.tier,
      createdAt: data.created_at
    };
  }
  
  return users.get(email);
}

export async function getUserByApiKey(apiKey: string): Promise<User | undefined> {
  if (isSupabaseConfigured()) {
    const { data, error } = await supabase
      .from('users')
      .select('*')
      .eq('api_key', apiKey)
      .single();
    
    if (error || !data) return undefined;
    
    return {
      id: data.id,
      email: data.email,
      passwordHash: data.password_hash,
      apiKey: data.api_key,
      role: data.role,
      tier: data.tier,
      createdAt: data.created_at
    };
  }
  
  return apiKeys.get(apiKey);
}

export async function updateUserApiKey(userId: string, newApiKey: string): Promise<boolean> {
  if (isSupabaseConfigured()) {
    const { error } = await supabase
      .from('users')
      .update({ api_key: newApiKey, updated_at: Date.now() })
      .eq('id', userId);
    
    if (error) {
      console.error('Failed to update API key in Supabase:', error);
      return false;
    }
  }
  
  // Update in-memory cache
  const user = users.get(userId);
  if (user) {
    apiKeys.delete(user.apiKey);
    user.apiKey = newApiKey;
    apiKeys.set(newApiKey, user);
    users.set(userId, user);
    users.set(user.email, user);
  }
  
  return true;
}

// ============================================
// Authentication Middleware
// ============================================

export async function authMiddleware(req: Request, res: Response, next: NextFunction): Promise<void> {
  const authHeader = req.headers.authorization;
  const apiKey = req.headers['x-api-key'] as string;
  
  // Try API key first
  if (apiKey) {
    const user = await getUserByApiKey(apiKey);
    if (user) {
      req.user = user;
      return next();
    }
  }
  
  // Try JWT token
  if (authHeader?.startsWith('Bearer ')) {
    const token = authHeader.substring(7);
    const decoded = verifyToken(token);
    
    if (decoded) {
      const user = await getUserById(decoded.id);
      if (user) {
        req.user = user;
        return next();
      }
    }
  }
  
  res.status(401).json({ 
    error: 'Unauthorized', 
    message: 'Valid API key or JWT token required' 
  });
}

// Optional auth - doesn't fail if no auth provided
export async function optionalAuth(req: Request, res: Response, next: NextFunction): Promise<void> {
  const authHeader = req.headers.authorization;
  const apiKey = req.headers['x-api-key'] as string;
  
  if (apiKey) {
    const user = await getUserByApiKey(apiKey);
    if (user) req.user = user;
  } else if (authHeader?.startsWith('Bearer ')) {
    const token = authHeader.substring(7);
    const decoded = verifyToken(token);
    if (decoded) {
      const user = await getUserById(decoded.id);
      if (user) req.user = user;
    }
  }
  
  next();
}

// Admin-only middleware
export async function adminOnly(req: Request, res: Response, next: NextFunction): Promise<void> {
  if (!req.user) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  
  if (req.user.role !== 'admin') {
    res.status(403).json({ error: 'Forbidden', message: 'Admin access required' });
    return;
  }
  
  next();
}

// Agent-only middleware (for fence clients)
export async function agentAuth(req: Request, res: Response, next: NextFunction): Promise<void> {
  if (!req.user) {
    res.status(401).json({ error: 'Unauthorized' });
    return;
  }
  
  if (req.user.role !== 'agent' && req.user.role !== 'admin') {
    res.status(403).json({ error: 'Forbidden', message: 'Agent access required' });
    return;
  }
  
  next();
}

// ============================================
// Rate limiting
// ============================================

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const rateLimits: Map<string, RateLimitEntry> = new Map();

export function rateLimit(maxRequests: number = 100, windowMs: number = 60000) {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    const key = req.user?.id || req.ip || 'anonymous';
    const now = Date.now();
    
    if (isSupabaseConfigured()) {
      // Use Supabase for rate limiting
      const { data, error } = await supabase
        .from('rate_limits')
        .select('*')
        .eq('key', key)
        .single();
      
      let entry: RateLimitEntry;
      
      if (error || !data || now > data.window_reset_at) {
        // Reset or create new entry
        entry = { count: 0, resetAt: now + windowMs };
        await supabase
          .from('rate_limits')
          .upsert({
            key,
            request_count: 0,
            window_reset_at: now + windowMs
          });
      } else {
        entry = { count: data.request_count, resetAt: data.window_reset_at };
      }
      
      entry.count++;
      
      await supabase
        .from('rate_limits')
        .update({ request_count: entry.count })
        .eq('key', key);
      
      res.setHeader('X-RateLimit-Limit', maxRequests);
      res.setHeader('X-RateLimit-Remaining', Math.max(0, maxRequests - entry.count));
      res.setHeader('X-RateLimit-Reset', entry.resetAt);
      
      if (entry.count > maxRequests) {
        res.status(429).json({ 
          error: 'Too Many Requests', 
          retryAfter: Math.ceil((entry.resetAt - now) / 1000) 
        });
        return;
      }
    } else {
      // Fallback to in-memory
      let entry = rateLimits.get(key);
      
      if (!entry || now > entry.resetAt) {
        entry = { count: 0, resetAt: now + windowMs };
        rateLimits.set(key, entry);
      }
      
      entry.count++;
      
      res.setHeader('X-RateLimit-Limit', maxRequests);
      res.setHeader('X-RateLimit-Remaining', Math.max(0, maxRequests - entry.count));
      res.setHeader('X-RateLimit-Reset', entry.resetAt);
      
      if (entry.count > maxRequests) {
        res.status(429).json({ 
          error: 'Too Many Requests', 
          retryAfter: Math.ceil((entry.resetAt - now) / 1000) 
        });
        return;
      }
    }
    
    next();
  };
}
