import request from 'supertest';
import app from './index';

describe('API Integration Tests', () => {
  let authToken: string;
  let apiKey: string;
  const testEmail = `test-${Date.now()}@example.com`;
  const testPassword = 'testpassword123';

  // Register and login to get a token before all tests
  beforeAll(async () => {
    // Register a test user
    const registerRes = await request(app)
      .post('/api/auth/register')
      .send({
        email: testEmail,
        password: testPassword,
        role: 'user'
      });

    if (registerRes.status === 200 || registerRes.status === 409) {
      // Login to get JWT
      const loginRes = await request(app)
        .post('/api/auth/login')
        .send({
          email: testEmail,
          password: testPassword
        });

      if (loginRes.status === 200) {
        authToken = loginRes.body.token;
        apiKey = loginRes.body.user?.apiKey;
      }
    }
  });

  describe('Health Endpoint', () => {
    it('GET /health should return 200 and status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('status', 'ok');
      expect(res.body).toHaveProperty('timestamp');
    });
  });

  describe('Auth Endpoints', () => {
    describe('POST /api/auth/register', () => {
      it('should register a new user successfully', async () => {
        const uniqueEmail = `newuser-${Date.now()}@example.com`;
        const res = await request(app)
          .post('/api/auth/register')
          .send({
            email: uniqueEmail,
            password: 'password123'
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('user');
        expect(res.body).toHaveProperty('token');
        expect(res.body.user).toHaveProperty('id');
        expect(res.body.user).toHaveProperty('email', uniqueEmail);
        expect(res.body.user).toHaveProperty('apiKey');
      });

      it('should reject registration without email', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({
            password: 'password123'
          });

        expect(res.status).toBe(400);
        expect(res.body).toHaveProperty('error');
      });

      it('should reject registration without password', async () => {
        const res = await request(app)
          .post('/api/auth/register')
          .send({
            email: `test-${Date.now()}@example.com`
          });

        expect(res.status).toBe(400);
        expect(res.body).toHaveProperty('error');
      });

      it('should reject duplicate email registration', async () => {
        const uniqueEmail = `dup-${Date.now()}@example.com`;

        // First registration
        await request(app)
          .post('/api/auth/register')
          .send({
            email: uniqueEmail,
            password: 'password123'
          });

        // Duplicate registration
        const res = await request(app)
          .post('/api/auth/register')
          .send({
            email: uniqueEmail,
            password: 'password123'
          });

        expect(res.status).toBe(409);
        expect(res.body).toHaveProperty('error');
      });
    });

    describe('POST /api/auth/login', () => {
      it('should login with valid credentials', async () => {
        const uniqueEmail = `login-${Date.now()}@example.com`;
        const password = 'password123';

        // Register first
        await request(app)
          .post('/api/auth/register')
          .send({ email: uniqueEmail, password });

        // Login
        const res = await request(app)
          .post('/api/auth/login')
          .send({ email: uniqueEmail, password });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('token');
        expect(res.body).toHaveProperty('user');
      });

      it('should reject login with invalid email', async () => {
        const res = await request(app)
          .post('/api/auth/login')
          .send({
            email: 'nonexistent@example.com',
            password: 'password123'
          });

        expect(res.status).toBe(401);
        expect(res.body).toHaveProperty('error');
      });

      it('should reject login with invalid password', async () => {
        const uniqueEmail = `badpass-${Date.now()}@example.com`;

        // Register first
        await request(app)
          .post('/api/auth/register')
          .send({ email: uniqueEmail, password: 'correctpassword' });

        // Login with wrong password
        const res = await request(app)
          .post('/api/auth/login')
          .send({
            email: uniqueEmail,
            password: 'wrongpassword'
          });

        expect(res.status).toBe(401);
        expect(res.body).toHaveProperty('error');
      });
    });

    describe('GET /api/auth/me', () => {
      it('should return user info with valid token', async () => {
        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', `Bearer ${authToken}`);

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('id');
        expect(res.body).toHaveProperty('email');
        expect(res.body).toHaveProperty('role');
      });

      it('should reject request without token', async () => {
        const res = await request(app).get('/api/auth/me');
        expect(res.status).toBe(401);
      });

      it('should reject request with invalid token', async () => {
        const res = await request(app)
          .get('/api/auth/me')
          .set('Authorization', 'Bearer invalid-token');

        expect(res.status).toBe(401);
      });
    });

    describe('POST /api/auth/refresh', () => {
      it('should refresh token with valid auth', async () => {
        // Create a separate user for this test to avoid affecting other tests
        const refreshEmail = `refresh-${Date.now()}@example.com`;
        await request(app)
          .post('/api/auth/register')
          .send({ email: refreshEmail, password: 'password123' });

        const loginRes = await request(app)
          .post('/api/auth/login')
          .send({ email: refreshEmail, password: 'password123' });

        const refreshToken = loginRes.body.token;

        const res = await request(app)
          .post('/api/auth/refresh')
          .set('Authorization', `Bearer ${refreshToken}`);

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('token');
        expect(res.body).toHaveProperty('expiresIn');
      });

      it('should reject refresh without token', async () => {
        const res = await request(app).post('/api/auth/refresh');
        expect(res.status).toBe(401);
      });
    });

    describe('POST /api/auth/refresh-key', () => {
      it('should refresh API key with valid auth', async () => {
        // Create a separate user for this test
        const keyEmail = `key-${Date.now()}@example.com`;
        await request(app)
          .post('/api/auth/register')
          .send({ email: keyEmail, password: 'password123' });

        const loginRes = await request(app)
          .post('/api/auth/login')
          .send({ email: keyEmail, password: 'password123' });

        const keyToken = loginRes.body.token;

        const res = await request(app)
          .post('/api/auth/refresh-key')
          .set('Authorization', `Bearer ${keyToken}`);

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('apiKey');
      });

      it('should reject refresh-key without token', async () => {
        const res = await request(app).post('/api/auth/refresh-key');
        expect(res.status).toBe(401);
      });
    });
  });

  describe('Agent Management Endpoints', () => {
    describe('POST /api/v1/agents', () => {
      it('should register an agent with valid auth', async () => {
        const res = await request(app)
          .post('/api/v1/agents')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            id: `test-agent-${Date.now()}`,
            name: 'Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('agentId');
      });

      it('should reject agent registration without auth', async () => {
        const res = await request(app)
          .post('/api/v1/agents')
          .send({
            id: 'test-agent',
            name: 'Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        expect(res.status).toBe(401);
      });
    });

    describe('POST /api/v1/validate', () => {
      it('should validate a transaction with valid auth', async () => {
        // First register an agent
        const agentId = `validate-agent-${Date.now()}`;
        await request(app)
          .post('/api/v1/agents')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            id: agentId,
            name: 'Validate Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        // Then validate
        const res = await request(app)
          .post('/api/v1/validate')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            agentId,
            action: 'read_file',
            target: '/tmp/test.txt',
            timestamp: Date.now()
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('allowed');
        expect(res.body).toHaveProperty('riskScore');
        expect(res.body).toHaveProperty('riskLevel');
        expect(res.body).toHaveProperty('reasons');
      });

      it('should reject validation without auth', async () => {
        const res = await request(app)
          .post('/api/v1/validate')
          .send({
            agentId: 'test-agent',
            action: 'read_file',
            target: '/tmp/test.txt',
            timestamp: Date.now()
          });

        expect(res.status).toBe(401);
      });
    });

    describe('GET /api/v1/agents/:agentId/status', () => {
      it('should get agent status with valid auth', async () => {
        const agentId = `status-agent-${Date.now()}`;

        // Register agent first
        await request(app)
          .post('/api/v1/agents')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            id: agentId,
            name: 'Status Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        // Get status
        const res = await request(app)
          .get(`/api/v1/agents/${agentId}/status`)
          .set('Authorization', `Bearer ${authToken}`);

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('agentId', agentId);
        expect(res.body).toHaveProperty('status');
      });

      it('should reject status request without auth', async () => {
        const res = await request(app)
          .get('/api/v1/agents/test-agent/status');

        expect(res.status).toBe(401);
      });
    });
  });

  describe('Kill Switch Endpoints', () => {
    describe('POST /api/v1/killswitch/trigger', () => {
      it('should trigger kill switch with valid auth', async () => {
        const agentId = `kill-agent-${Date.now()}`;

        // Register agent first
        await request(app)
          .post('/api/v1/agents')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            id: agentId,
            name: 'Kill Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        // Trigger kill
        const res = await request(app)
          .post('/api/v1/killswitch/trigger')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            agentId,
            reason: 'Test kill'
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('triggered', true);
      });

      it('should reject kill trigger without auth', async () => {
        const res = await request(app)
          .post('/api/v1/killswitch/trigger')
          .send({
            agentId: 'test-agent',
            reason: 'Test kill'
          });

        expect(res.status).toBe(401);
      });
    });

    describe('GET /api/v1/killswitch/status', () => {
      it('should get kill switch status', async () => {
        const res = await request(app).get('/api/v1/killswitch/status');
        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('globalKillActive');
      });
    });
  });

  describe('Runtime Fence Endpoints', () => {
    describe('GET /api/runtime/status', () => {
      it('should get runtime status', async () => {
        const res = await request(app).get('/api/runtime/status');
        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('operational');
        expect(res.body).toHaveProperty('globalKillActive');
        expect(res.body).toHaveProperty('version');
        expect(res.body).toHaveProperty('uptime');
        expect(res.body).toHaveProperty('timestamp');
      });
    });

    describe('POST /api/runtime/assess', () => {
      it('should assess action with agent auth', async () => {
        // Create an agent-role user for this test
        const agentUserEmail = `agentuser-${Date.now()}@example.com`;
        await request(app)
          .post('/api/auth/register')
          .send({ email: agentUserEmail, password: 'password123', role: 'agent' });

        const loginRes = await request(app)
          .post('/api/auth/login')
          .send({ email: agentUserEmail, password: 'password123' });

        const agentToken = loginRes.body.token;
        const agentId = `assess-agent-${Date.now()}`;

        // Register agent first
        await request(app)
          .post('/api/v1/agents')
          .set('Authorization', `Bearer ${agentToken}`)
          .send({
            id: agentId,
            name: 'Assess Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        // Assess action
        const res = await request(app)
          .post('/api/runtime/assess')
          .set('Authorization', `Bearer ${agentToken}`)
          .send({
            agentId,
            action: 'read_file',
            context: { target: '/tmp/test.txt' }
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('agentId', agentId);
        expect(res.body).toHaveProperty('riskScore');
        expect(res.body).toHaveProperty('riskLevel');
        expect(res.body).toHaveProperty('allowed');
        expect(res.body).toHaveProperty('reasons');
        expect(res.body).toHaveProperty('timestamp');
      });

      it('should reject assess without auth', async () => {
        const res = await request(app)
          .post('/api/runtime/assess')
          .send({
            agentId: 'test-agent',
            action: 'read_file'
          });

        expect(res.status).toBe(401);
      });

      it('should reject assess with non-agent user', async () => {
        // Regular user token should be rejected for agent-only endpoint
        const res = await request(app)
          .post('/api/runtime/assess')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            agentId: 'test-agent',
            action: 'read_file',
            context: { target: '/tmp/test.txt' }
          });

        expect(res.status).toBe(403);
      });
    });

    describe('POST /api/runtime/kill', () => {
      it('should kill agent with valid auth', async () => {
        const agentId = `runtime-kill-agent-${Date.now()}`;

        // Register agent first
        await request(app)
          .post('/api/v1/agents')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            id: agentId,
            name: 'Runtime Kill Test Agent',
            owner: 'user-1',
            permissions: ['read']
          });

        // Kill agent
        const res = await request(app)
          .post('/api/runtime/kill')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            agentId,
            reason: 'Test kill',
            immediate: true
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('agentId', agentId);
        expect(res.body).toHaveProperty('status', 'terminated');
        expect(res.body).toHaveProperty('timestamp');
      });

      it('should reject kill without auth', async () => {
        const res = await request(app)
          .post('/api/runtime/kill')
          .send({
            agentId: 'test-agent',
            reason: 'Test kill'
          });

        expect(res.status).toBe(401);
      });
    });
  });

  describe('Audit Endpoints', () => {
    describe('POST /api/audit/submit', () => {
      it('should submit audit request with valid auth', async () => {
        const res = await request(app)
          .post('/api/audit/submit')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            contractAddress: '0x1234567890abcdef',
            auditType: 'basic'
          });

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('success', true);
        expect(res.body).toHaveProperty('auditId');
        expect(res.body).toHaveProperty('audit');
      });

      it('should reject audit submission without auth', async () => {
        const res = await request(app)
          .post('/api/audit/submit')
          .send({
            contractAddress: '0x1234567890abcdef',
            auditType: 'basic'
          });

        expect(res.status).toBe(401);
      });
    });

    describe('GET /api/audit/list', () => {
      it('should list audits with valid auth', async () => {
        const res = await request(app)
          .get('/api/audit/list')
          .set('Authorization', `Bearer ${authToken}`);

        expect(res.status).toBe(200);
        expect(res.body).toHaveProperty('audits');
        expect(Array.isArray(res.body.audits)).toBe(true);
      });

      it('should reject list request without auth', async () => {
        const res = await request(app).get('/api/audit/list');
        expect(res.status).toBe(401);
      });
    });
  });
});
