import { createClient } from '@supabase/supabase-js';

// Get environment variables with fallbacks for build time
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY || 'placeholder-service-key';

// Validate only at runtime, not during build
function validateEnv() {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    throw new Error('Missing environment variable: NEXT_PUBLIC_SUPABASE_URL');
  }
  if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    throw new Error('Missing environment variable: NEXT_PUBLIC_SUPABASE_ANON_KEY');
  }
  if (!process.env.SUPABASE_SERVICE_KEY) {
    throw new Error('Missing environment variable: SUPABASE_SERVICE_KEY');
  }
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Server-side client with service role (use only in API routes)
export const supabaseAdmin = createClient(
  supabaseUrl,
  supabaseServiceKey,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  }
);

// Export validation function for explicit checks
export { validateEnv };