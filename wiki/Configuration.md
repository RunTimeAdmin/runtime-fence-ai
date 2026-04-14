# Configuration

Configure $KILLSWITCH to match your security requirements.

## FenceConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `agent_id` | string | required | Unique identifier for this agent |
| `offline_mode` | bool | False | Skip API calls, local validation only |
| `blocked_actions` | list | [] | Actions to always block |
| `blocked_targets` | list | [] | Targets to always block |
| `spending_limit` | float | None | Max spending allowed |
| `risk_threshold` | str | "medium" | Acceptable risk level: low/medium/high |
| `auto_kill_on_critical` | bool | True | Auto-kill on critical risk |
| `preset` | str | None | Use a preset configuration |

## Example Configuration

```python
from runtime_fence import RuntimeFence, FenceConfig

config = FenceConfig(
    agent_id="production-agent",
    offline_mode=False,
    blocked_actions=["delete", "exec", "sudo", "drop_table"],
    blocked_targets=[".env", "production", "wallet", "credentials"],
    spending_limit=100.0,
    risk_threshold="medium",
    auto_kill_on_critical=True
)

fence = RuntimeFence(config)
```

## Environment Variables

### API Connection
```bash
RUNTIME_FENCE_API_URL=http://localhost:3001
RUNTIME_FENCE_API_KEY=ks_your_api_key
```

### Email Alerts
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_TO_EMAILS=admin@company.com,security@company.com
```

### SMS Alerts (Twilio)
```bash
TWILIO_SID=your_account_sid
TWILIO_TOKEN=your_auth_token
TWILIO_FROM=+1234567890
ALERT_SMS_NUMBERS=+1234567890,+0987654321
```

## Settings File

You can also use a JSON config file:

```json
{
  "agent_id": "my-agent",
  "blocked_actions": ["delete", "exec"],
  "blocked_targets": [".env", "production"],
  "spending_limit": 100,
  "risk_threshold": "medium",
  "auto_kill_on_critical": true
}
```

Load it:
```python
import json
from runtime_fence import RuntimeFence, FenceConfig

with open("fence_config.json") as f:
    data = json.load(f)

config = FenceConfig(**data)
fence = RuntimeFence(config)
```

## Risk Thresholds

| Level | Score Range | Behavior |
|-------|-------------|----------|
| `low` | 0-33 | Allow only low-risk actions |
| `medium` | 0-66 | Allow low and medium-risk actions |
| `high` | 0-100 | Allow all except critical |

Actions exceeding the threshold are blocked.

## Safe Resume Modes

After a kill switch activation, you can resume with different modes:

```python
from safe_resume import SafeResume, ResumeMode

# Immediate resume (not recommended)
SafeResume.resume("agent-1", ResumeMode.IMMEDIATE)

# Cooldown period (wait 5 minutes)
SafeResume.resume("agent-1", ResumeMode.COOLDOWN, cooldown_seconds=300)

# Require approval
SafeResume.request_approval("agent-1", approver_email="admin@company.com")

# Gradual resume (start at 10% capacity)
SafeResume.resume("agent-1", ResumeMode.GRADUAL, start_capacity=0.1)
```

## Alerts Configuration

```python
from alerts import AlertManager

alerts = AlertManager(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_user="alerts@company.com",
    smtp_password="app_password",
    to_emails=["admin@company.com"],
    twilio_sid="AC...",
    twilio_token="...",
    twilio_from="+1234567890",
    sms_numbers=["+1987654321"]
)

# Send alert
alerts.send_alert(
    title="Kill Switch Activated",
    message="Agent xyz was killed due to suspicious activity",
    severity="high"
)
```

## Logging

Audit logs are stored in `~/.fence/audit/`:

```
~/.fence/audit/
├── 2026-02-01.jsonl
├── 2026-02-02.jsonl
└── ...
```

Each line is a JSON object:
```json
{"timestamp":1234567890,"agentId":"xyz","action":"delete","target":"file","result":"blocked","riskScore":85}
```
