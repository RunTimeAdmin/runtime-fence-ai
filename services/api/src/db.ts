import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;

// Create a mock Supabase client for testing when credentials are not available
function createMockClient(): SupabaseClient {
  return {
    from: () => ({
      select: () => ({ eq: () => ({ single: () => Promise.resolve({ data: null, error: null }) }) }),
      insert: () => Promise.resolve({ data: null, error: null }),
      update: () => ({ eq: () => Promise.resolve({ data: null, error: null }) }),
      delete: () => ({ eq: () => Promise.resolve({ data: null, error: null }) }),
      upsert: () => Promise.resolve({ data: null, error: null }),
    }),
    auth: {
      signUp: () => Promise.resolve({ data: null, error: null }),
      signIn: () => Promise.resolve({ data: null, error: null }),
    },
  } as unknown as SupabaseClient;
}

export const supabase: SupabaseClient = (supabaseUrl && supabaseKey)
  ? createClient(supabaseUrl, supabaseKey)
  : createMockClient();

export function isSupabaseConfigured(): boolean {
  return !!(supabaseUrl && supabaseKey && supabaseUrl !== 'https://your-project.supabase.co');
}
