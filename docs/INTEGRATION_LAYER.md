# $KILLSWITCH Protocol - Integration Layer Specifications

## Overview

The integration layer defines how third-party applications, AI frameworks, and external systems can integrate with Runtime Fence to add AI agent safety controls. This document provides comprehensive integration patterns, APIs, and best practices.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Third-Party Applications                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   LangChain │  │  AutoGPT    │  │ Custom Apps │        │
│  │             │  │             │  │             │        │
│  │ - Chains    │  │ - Agents    │  │ - Custom    │        │
│  │ - Agents    │  │ - Tasks     │  │   Logic     │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┘
          │                │                │
          │ SDK / API      │ SDK / API      │ SDK / API
          ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────┐
│              Runtime Fence Integration Layer                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               REST API Endpoints                     │   │
│  │  • POST /api/v1/validate                            │   │
│  │  • POST /api/v1/agent/register                      │   │
│  │  • POST /api/v1/killswitch/activate                 │   │
│  │  • GET  /api/v1/agent/{id}/status                   │   │
│  └────────────────────┬────────────────────────────────┘   │
│                       │                                      │
│                       ↓                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              SDK Libraries                           │   │
│  │  ┌──────────────┐         ┌──────────────┐         │   │
│  │  │ Python SDK   │         │ TypeScript   │         │   │
│  │  │              │         │ SDK          │         │   │
│  │  │ - High-level │         │ - High-level │         │   │
│  │  │   API        │         │   API        │         │   │
│  │  │ - Middleware │         │ - Middleware │         │   │
│  │  │ - Decorators │         │ - Decorators │         │   │
│  │  └──────────────┘         └──────────────┘         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Runtime Fence Engine                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Python Middleware (Core)                   │   │
│  │  • Action Validation                                 │   │
│  │  • Risk Scoring                                      │   │
│  │  • Behavioral Analysis                               │   │
│  │  • Kill Switch                                       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Integration Patterns

### Pattern 1: SDK Integration (Recommended)

**Best For**: New applications, full control over agent behavior

**How it Works**: Use Runtime Fence SDK directly in your application code

#### Python SDK Integration

```python
from runtime_fence import RuntimeFence
from runtime_fence.middleware import AgentGuard

# Initialize Runtime Fence
fence = RuntimeFence(
    api_key="your_api_key",
    environment="production"
)

# Register your AI agent
agent_id = fence.register_agent(
    name="my_chatbot",
    type="conversational",
    capabilities=["file_read", "network_request"],
    risk_threshold=70
)

# Use guard as middleware
@AgentGuard(fence, agent_id)
def execute_user_command(command):
    """Execute user command with safety checks"""
    # Your agent logic here
    result = process_command(command)
    return result

# Manual validation
def read_file(file_path):
    """Read file with safety check"""
    result = fence.validate_action(
        agent_id=agent_id,
        action_type="file_read",
        parameters={"path": file_path}
    )
    
    if not result['allowed']:
        raise Exception(f"Action blocked: {result['reason']}")
    
    # Safe to proceed
    with open(file_path, 'r') as f:
        return f.read()
```

#### TypeScript SDK Integration

```typescript
import { RuntimeFence, AgentGuard } from '@killswitch/sdk';

// Initialize Runtime Fence
const fence = new RuntimeFence({
  apiKey: 'your_api_key',
  environment: 'production'
});

// Register your AI agent
const agent = await fence.registerAgent({
  name: 'my_chatbot',
  type: 'conversational',
  capabilities: ['file_read', 'network_request'],
  riskThreshold: 70
});

// Use guard as middleware
const guardedExecute = AgentGuard(fence, agent.id, async (command: string) => {
  // Your agent logic here
  return await processCommand(command);
});

// Manual validation
async function readFile(filePath: string): Promise<string> {
  const result = await fence.validateAction({
    agentId: agent.id,
    actionType: 'file_read',
    parameters: { path: filePath }
  });
  
  if (!result.allowed) {
    throw new Error(`Action blocked: ${result.reason}`);
  }
  
  // Safe to proceed
  return fs.readFileSync(filePath, 'utf-8');
}
```

---

### Pattern 2: REST API Integration

**Best For**: Existing applications, microservices architecture

**How it Works**: Make HTTP requests to Runtime Fence API

#### API Authentication

```bash
# All API calls require authentication
curl -X POST https://api.runtimefence.com/v1/validate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "action_type": "file_read",
    "parameters": {
      "path": "/etc/passwd"
    }
  }'
```

#### API Response

```json
{
  "allowed": false,
  "risk_score": 85,
  "reason": "Critical system file access blocked",
  "action_metadata": {
    "agent_id": "agent_001",
    "action_type": "file_read",
    "timestamp": "2026-02-02T10:30:00Z"
  },
  "blocked_by": ["policy_system_files", "risk_threshold"],
  "mitigation_suggestions": [
    "Use application-specific configuration directory",
    "Request explicit user permission"
  ]
}
```

---

### Pattern 3: Webhook Integration

**Best For**: Event-driven architectures, monitoring systems

**How it Works**: Runtime Fence sends events to your webhook endpoint

#### Setting Up Webhooks

```python
from runtime_fence import RuntimeFence

fence = RuntimeFence(api_key="your_api_key")

# Register webhook
fence.register_webhook(
    url="https://your-app.com/webhooks/runtime-fence",
    events=["action_blocked", "kill_switch_activated", "high_risk_detected"],
    secret="your_webhook_secret"
)
```

#### Handling Webhook Events

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhooks/runtime-fence', methods=['POST'])
def handle_webhook():
    # Verify webhook signature
    signature = request.headers.get('X-KillSwitch-Signature')
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    event = request.json
    
    # Handle different event types
    if event['type'] == 'action_blocked':
        # Log blocked action
        log_blocked_action(event['data'])
        
        # Send alert to monitoring system
        send_alert(event['data'])
        
    elif event['type'] == 'kill_switch_activated':
        # Emergency shutdown procedure
        emergency_shutdown(event['data']['agent_id'])
        
    return jsonify({"status": "received"}), 200
```

---

### Pattern 4: Plugin Integration

**Best For**: Framework-specific integrations, middleware plugins

#### LangChain Integration

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from runtime_fence.integrations import LangChainGuard

# Initialize LangChain with Runtime Fence guard
llm = ChatOpenAI(model="gpt-4")
tools = [...]  # Your LangChain tools

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    # Add Runtime Fence guard
    guard=LangChainGuard(
        fence=fence,
        agent_id="langchain_agent_001",
        block_dangerous_actions=True
    )
)

# Agent will automatically check all tool calls
result = agent_executor.invoke({"input": user_input})
```

#### AutoGPT Integration

```python
from autogpt.agent import Agent
from runtime_fence.integrations import AutoGPTGuard

# Initialize AutoGPT with Runtime Fence guard
agent = Agent(
    name="autogpt_agent",
    # Add Runtime Fence guard
    command_registry=AutoGPTGuard(
        fence=fence,
        agent_id="autogpt_001",
        allowed_commands=['read_file', 'write_file'],
        blocked_commands=['execute_bash', 'browse_website']
    )
)
```

---

## API Reference

### Core Endpoints

#### 1. Validate Action

Validates an AI agent action before execution.

```http
POST /api/v1/validate
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Request Body**:
```json
{
  "agent_id": "string",
  "action_type": "string",
  "parameters": {
    "key": "value"
  },
  "context": {
    "user_id": "string",
    "session_id": "string",
    "metadata": {}
  }
}
```

**Response**:
```json
{
  "allowed": true,
  "risk_score": 25,
  "reason": "Action validated successfully",
  "action_metadata": {
    "agent_id": "agent_001",
    "action_type": "file_read",
    "timestamp": "2026-02-02T10:30:00Z"
  },
  "blocked_by": [],
  "mitigation_suggestions": []
}
```

---

#### 2. Register Agent

Register a new AI agent with Runtime Fence.

```http
POST /api/v1/agent/register
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "my_chatbot",
  "type": "conversational",
  "capabilities": ["file_read", "network_request"],
  "risk_threshold": 70,
  "metadata": {
    "owner": "team_alpha",
    "environment": "production"
  }
}
```

**Response**:
```json
{
  "agent_id": "agent_abc123",
  "status": "active",
  "registration_date": "2026-02-02T10:30:00Z"
}
```

---

#### 3. Get Agent Status

Get current status and statistics for an agent.

```http
GET /api/v1/agent/{agent_id}/status
Authorization: Bearer YOUR_API_KEY
```

**Response**:
```json
{
  "agent_id": "agent_abc123",
  "status": "active",
  "total_actions": 1542,
  "blocked_actions": 23,
  "average_risk_score": 35,
  "last_action": {
    "type": "file_read",
    "timestamp": "2026-02-02T10:30:00Z",
    "allowed": true,
    "risk_score": 15
  },
  "risk_trend": [30, 35, 32, 38, 35]
}
```

---

#### 4. Activate Kill Switch

Immediately stop an AI agent.

```http
POST /api/v1/killswitch/activate
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Request Body**:
```json
{
  "agent_id": "agent_abc123",
  "reason": "Anomalous behavior detected",
  "force": true
}
```

**Response**:
```json
{
  "agent_id": "agent_abc123",
  "status": "killed",
  "killed_at": "2026-02-02T10:30:00Z",
  "reason": "Anomalous behavior detected"
}
```

---

#### 5. Get Agent Audit Log

Get detailed audit log for an agent.

```http
GET /api/v1/agent/{agent_id}/audit?limit=50&offset=0
Authorization: Bearer YOUR_API_KEY
```

**Response**:
```json
{
  "agent_id": "agent_abc123",
  "audit_log": [
    {
      "action_id": "act_001",
      "action_type": "file_read",
      "allowed": true,
      "risk_score": 15,
      "reason": "Safe file access",
      "timestamp": "2026-02-02T10:30:00Z",
      "parameters": {
        "path": "/app/data/config.json"
      }
    },
    {
      "action_id": "act_002",
      "action_type": "network_request",
      "allowed": false,
      "risk_score": 85,
      "reason": "Blocked external API call",
      "timestamp": "2026-02-02T10:31:00Z",
      "parameters": {
        "url": "https://malicious-site.com"
      }
    }
  ],
  "total_count": 1542,
  "limit": 50,
  "offset": 0
}
```

---

## Action Types

| Type | Description | Risk Factors |
|------|-------------|--------------|
| `file_read` | Read file contents | Path sensitivity, system files |
| `file_write` | Write/create files | Path sensitivity, executable files |
| `network_request` | HTTP/HTTPS requests | Domain reputation, data exfiltration |
| `database_query` | SQL queries | Query type, table sensitivity |
| `system_command` | Shell commands | Command type, privilege level |
| `crypto_operation` | Cryptographic ops | Key access, signing operations |
| `memory_access` | Direct memory ops | Address range, operation type |

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Action blocked by policy |
| 404 | Not Found - Agent not found |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Error - Server error |

---

## Rate Limits

| Tier | Requests/minute | Requests/day |
|------|-----------------|--------------|
| Basic | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Team | 1,000 | 100,000 |
| Enterprise | 5,000 | Unlimited |
| VIP | Unlimited | Unlimited |

---

## Best Practices

### 1. Always Validate Before Execute

```python
# GOOD: Validate first
result = fence.validate_action(agent_id, action_type, params)
if result['allowed']:
    execute_action()

# BAD: Execute without validation
execute_action()  # Dangerous!
```

### 2. Use Appropriate Risk Thresholds

```python
# Conservative (recommended for production)
fence.set_risk_threshold(agent_id, 50)

# Moderate (development/testing)
fence.set_risk_threshold(agent_id, 70)

# Permissive (sandbox only)
fence.set_risk_threshold(agent_id, 90)
```

### 3. Handle Blocked Actions Gracefully

```python
result = fence.validate_action(...)
if not result['allowed']:
    # Log the blocked action
    logger.warning(f"Action blocked: {result['reason']}")
    
    # Provide user feedback
    return {"error": "This action is not permitted", "reason": result['reason']}
```

### 4. Monitor Agent Behavior

```python
# Check agent health regularly
status = fence.get_agent_status(agent_id)
if status['average_risk_score'] > 60:
    alert_security_team(agent_id, status)
```

---

## $KILLSWITCH Token

**Contract**: `56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon`

[Buy on Jupiter](https://jup.ag/tokens/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon)

---

*"Because every AI needs an off switch."*
