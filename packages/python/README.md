# Runtime Fence - Universal AI Agent Kill Switch

Stop **ANY** AI agent from going rogue. Works with coding assistants, autonomous agents, trading bots, data analysts, web scrapers, and more.

**Supports:** LangChain • AutoGPT • Copilot • Cursor • Aider • CrewAI • BabyAGI • Custom Agents

## Installation

```bash
pip install runtime-fence
```

## Quick Start

```python
from runtime_fence import RuntimeFence, FenceConfig

# Create fence with your safety rules
fence = RuntimeFence(FenceConfig(
    agent_id="my-agent",
    blocked_actions=["delete", "exec", "rm"],
    blocked_targets=["production", ".env"],
    spending_limit=100.0
))

# Validate before allowing
result = fence.validate("delete", "user_data.sql")

if result.allowed:
    # Safe to proceed
    delete_file("user_data.sql")
else:
    print(f"Blocked: {result.reasons}")

# Emergency stop
fence.kill("Suspicious behavior detected")
```

## Configuration

### Basic Configuration

```python
from runtime_fence import RuntimeFence, FenceConfig, RiskLevel

config = FenceConfig(
    agent_id="my-agent",           # Unique identifier
    blocked_actions=[              # Actions to block
        "delete", "exec", "rm", "sudo"
    ],
    blocked_targets=[              # Targets to protect
        "production", ".env", "api_keys"
    ],
    spending_limit=100.0,          # Max dollars to spend
    risk_threshold=RiskLevel.MEDIUM,  # Blocking threshold
    auto_kill_on_critical=True,    # Auto-kill on critical risk
    offline_mode=False             # Work without API
)

fence = RuntimeFence(config)
```

### Presets for Common Use Cases

**Coding Assistant (Cursor, Copilot, Aider):**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="coding-assistant",
    blocked_actions=["exec", "shell", "rm", "sudo"],
    blocked_targets=["production", ".env", "/etc/"],
    spending_limit=10.0
))
```

**Autonomous Agents (AutoGPT, BabyAGI):**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="autogpt",
    blocked_actions=["spawn_agent", "modify_self", "execute_code"],
    blocked_targets=["system_files", "config"],
    spending_limit=50.0
))
```

**Data Analyst:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="data-analyst",
    blocked_actions=["delete", "drop_table", "truncate"],
    blocked_targets=["pii", "ssn", "credit_card"],
    spending_limit=50.0
))
```

**Web Automation:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="web-automator",
    blocked_actions=["login", "purchase", "checkout"],
    spending_limit=0.0  # No spending
))
```

**Trading Bot:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="trading-bot",
    blocked_actions=["withdraw", "transfer"],
    blocked_targets=["wallet_private_key"],
    spending_limit=1000.0
))
```

**LangChain Integration:**
```python
from langchain_integration import create_fenced_agent, Preset

agent = create_fenced_agent(
    preset=Preset.CODING_ASSISTANT,
    agent_id="langchain-coder"
)
```

## Features

- **Kill Switch** - Stop any agent instantly (<100ms)
- **Action Blocking** - Define forbidden actions
- **Target Protection** - Block sensitive files/APIs
- **Spending Limits** - Control costs
- **Risk Scoring** - Automatic risk assessment
- **Audit Logging** - Complete action history
- **Offline Mode** - Works without external API

## Decorator Usage

```python
@fence.wrap_function("api_call", "external_service")
def call_external_api(data):
    return requests.post("https://api.example.com", json=data)

# Automatically validated through fence
call_external_api({"key": "value"})
```

## CLI Commands

```bash
fence test      # Run validation tests
fence status    # Show fence status
fence version   # Check version
```

## Links

- **GitHub:** https://github.com/RunTimeAdmin/runtime-fence-ai
- **Documentation:** https://github.com/RunTimeAdmin/runtime-fence-ai/wiki
- **Issues:** https://github.com/RunTimeAdmin/runtime-fence-ai/issues

## License

MIT License - see LICENSE file for details 
