# API Reference

$KILLSWITCH REST API documentation.

## Authentication

All protected endpoints require authentication via JWT token or API key.

### JWT Token
```
Authorization: Bearer <token>
```

### API Key
```
X-API-Key: ks_xxxxxxxxxxxxx
```

## Endpoints

### Auth

#### POST /api/auth/register
Create a new account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "role": "user"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "role": "user",
    "apiKey": "ks_xxxxx"
  },
  "token": "eyJhbG..."
}
```

#### POST /api/auth/login
Get a JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbG..."
}
```

### Runtime

#### POST /api/runtime/assess
Validate an action through the fence.

**Request:**
```json
{
  "agentId": "my-agent",
  "action": "delete",
  "context": {
    "target": "database",
    "amount": 0
  }
}
```

**Response:**
```json
{
  "agentId": "my-agent",
  "riskScore": 75,
  "riskLevel": "high",
  "allowed": false,
  "reasons": ["Action 'delete' is blocked"],
  "timestamp": 1234567890
}
```

#### POST /api/runtime/kill
Activate the kill switch.

**Request:**
```json
{
  "agentId": "my-agent",
  "reason": "Suspicious activity detected",
  "immediate": true
}
```

**Response:**
```json
{
  "success": true,
  "agentId": "my-agent",
  "status": "terminated",
  "timestamp": 1234567890
}
```

#### GET /api/runtime/status
Get current fence status.

**Response:**
```json
{
  "operational": true,
  "globalKillActive": false,
  "version": "1.0.0",
  "uptime": 3600,
  "timestamp": 1234567890
}
```

### Settings

#### GET /api/settings
Get user settings.

**Response:**
```json
{
  "userId": "user_abc123",
  "preset": "coding",
  "blockedActions": ["exec", "rm", "sudo"],
  "blockedTargets": [".env", ".ssh"],
  "spendingLimit": 0,
  "riskThreshold": "medium",
  "autoKill": true,
  "offlineMode": false
}
```

#### POST /api/settings
Update settings.

**Request:**
```json
{
  "preset": "custom",
  "blockedActions": ["delete", "exec"],
  "blockedTargets": ["production"],
  "spendingLimit": 100,
  "riskThreshold": "high"
}
```

### Audit Logs

#### GET /api/audit-logs
Get audit log entries.

**Query Parameters:**
- `limit` - Number of entries (default: 100)
- `offset` - Pagination offset
- `agentId` - Filter by agent
- `action` - Filter by action
- `result` - Filter by result (allowed/blocked/killed)

**Response:**
```json
{
  "total": 500,
  "offset": 0,
  "limit": 100,
  "logs": [
    {
      "id": "LOG-abc123",
      "timestamp": 1234567890,
      "agentId": "my-agent",
      "action": "read",
      "target": "file.txt",
      "result": "allowed",
      "riskScore": 0
    }
  ]
}
```

#### GET /api/audit-logs/stats
Get audit statistics.

**Response:**
```json
{
  "totalEvents": 1000,
  "allowed": 900,
  "blocked": 95,
  "killed": 5,
  "avgRiskScore": 15,
  "topBlockedActions": [
    {"value": "delete", "count": 50},
    {"value": "exec", "count": 30}
  ]
}
```

## Rate Limiting

- 100 requests per minute per user
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Error Responses

```json
{
  "error": "Unauthorized",
  "message": "Valid API key or JWT token required"
}
```

Common status codes:
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not found
- `429` - Rate limit exceeded
- `500` - Internal server error
