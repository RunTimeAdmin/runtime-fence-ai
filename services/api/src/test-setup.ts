// Test setup file
// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = process.env.JWT_SECRET || 'test-secret-for-unit-tests-do-not-use-in-production';
process.env.SUPABASE_URL = process.env.SUPABASE_URL || '';
process.env.SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
