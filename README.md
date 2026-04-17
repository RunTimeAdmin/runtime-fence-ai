# Runtime Fence

**Universal AI Agent Safety Control - Emergency kill switch for ANY AI agent**

Runtime Fence is a comprehensive safety ecosystem for ALL AI agents. Whether it's a coding assistant, autonomous agent, trading bot, or data analyst - instantly stop any agent, block dangerous actions, and monitor everything in real-time.

**Works with:** LangChain • AutoGPT • Copilot • Cursor • Aider • CrewAI • BabyAGI • Custom Agents • Trading Bots • Email Bots • Web Scrapers • Data Analysts

**🌐 Live Demo:** [runtimefence.com](https://runtimefence.com)

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/RunTimeAdmin/runtime-fence-ai/actions) [![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE) [![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![PyPI](https://img.shields.io/badge/pypi-runtime--fence-blue)](https://pypi.org/project/runtime-fence/)

---

## 🚀 Features

### Core Capabilities

- **🔴 Kill Switch** - Instantly stop any AI agent with one click
- **🚫 Action Blocking** - Define what actions agents cannot take
- **🛡️ Target Protection** - Block access to sensitive files, APIs, or systems
- **💰 Spending Limits** - Control how much an agent can spend
- **📊 Risk Scoring** - Automatic risk assessment of every action
- **📝 Audit Logging** - Complete trail of all agent activity
- **📧 Email/SMS Alerts** - Get notified of suspicious behavior
- **🖥️ Cross-Platform** - Windows, macOS, and Linux support

### Security Hardening (6 Core Modules)

- **🔒 Runtime Fence** - Real-time action validation and monitoring
- **☠️ Kill Switch** - SIGTERM → SIGKILL emergency termination
- **📝 Audit Logging** - Complete cryptographic audit trail
- **⚡ Sub-Second Response** - Kill signals under 100ms
- **🛡️ Offline Mode** - Works without external dependencies
- **🎯 Risk Scoring** - Automatic threat assessment (0-100)

### Production Tamper Detection

Runtime Fence includes SHA-256 hash verification of all critical security modules. For production deployments, freeze hashes at build time:

```bash
cd packages/python
python freeze_hashes.py > runtime_fence/_frozen_hashes.py
```

This generates `_frozen_hashes.py` containing SHA-256 hashes of all 9 security modules. At runtime, `bypass_protection.py` compares live file hashes against frozen values — any mismatch triggers a tamper alert.

**CI/CD Integration:**

Add to your build pipeline (after tests pass, before packaging):

```yaml
# GitHub Actions example
- name: Freeze security hashes
  run: |
    cd packages/python
    python freeze_hashes.py > runtime_fence/_frozen_hashes.py
    
- name: Verify frozen hashes
  run: python -c "from runtime_fence._frozen_hashes import FROZEN_HASHES; print(f'{len(FROZEN_HASHES)} modules frozen')"
```

> **Important:** Re-run `freeze_hashes.py` after any change to security modules. Without frozen hashes, tamper detection falls back to runtime-computed hashes with a warning log.

---

## 📦 Quick Start

### Installation

```bash
pip install runtime-fence
```

Or clone and install:

```bash
git clone https://github.com/RunTimeAdmin/runtime-fence-ai.git
cd runtime-fence-ai/packages/python
pip install -e .
```

### Basic Usage

```python
from runtime_fence import RuntimeFence, FenceConfig

# Create a fence
fence = RuntimeFence(FenceConfig(
    agent_id="my-agent",
    blocked_actions=["delete", "exec", "sudo"],
    blocked_targets=[".env", "production", "wallet"],
    spending_limit=100.0
))

# Validate an action
result = fence.validate("read", "document.txt")
if result.allowed:
    # Proceed with action
    pass
else:
    print(f"Blocked: {result.reasons}")

# Kill switch
fence.kill("Emergency stop")
```

### Wrap Any Function

```python
@fence.wrap_function("api_call", "external_service")
def call_external_api(data):
    return requests.post("https://api.example.com", json=data)

# Now the function goes through the fence automatically
call_external_api({"key": "value"})
```

---

## 🖥️ Desktop App (System Tray)

### Windows

```bash
install_fence.bat
```

### Mac/Linux

```bash
chmod +x install_fence.sh
./install_fence.sh
```

Look for the shield icon in your system tray. Right-click for options.

---

## ⌨️ CLI Commands

```bash
fence version --check    # Check for updates
fence update             # Upgrade to latest version
fence status             # Show fence status
fence scan               # Detect AI agents on your system
fence test               # Run quick validation test
fence start              # Launch tray app
```

---

## 🤖 Universal Agent Protection

Runtime Fence works with **ANY** Python-based AI agent. Here are real-world examples:

### Coding Assistants
**Agents:** GitHub Copilot, Cursor, Aider, Cody  
**Risks Blocked:** Executing shell commands, deleting files, modifying system configs  
**Example:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="cursor-assistant",
    blocked_actions=["exec", "shell", "rm", "sudo"],
    blocked_targets=[".git/", ".env", "~/.ssh/"]
))
```

### Autonomous Agents  
**Agents:** AutoGPT, BabyAGI, AgentGPT, SuperAGI  
**Risks Blocked:** Self-modification, spawning agents, unrestricted API calls  
**Example:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="autogpt",
    blocked_actions=["spawn_agent", "modify_self", "execute_code"],
    spending_limit=50.0
))
```

### Data Analysts
**Agents:** LangChain data agents, Pandas AI, custom ETL bots  
**Risks Blocked:** Deleting databases, exporting PII, dropping tables  
**Example:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="data-analyst",
    blocked_actions=["delete", "drop_table", "export_pii"],
    blocked_targets=["production_db", "customer_data"]
))
```

### Web Automation
**Agents:** Selenium bots, Playwright agents, web scrapers  
**Risks Blocked:** Form submissions, purchases, credential theft  
**Example:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="web-scraper",
    blocked_actions=["login", "purchase", "submit_form"],
    blocked_targets=["payment", "checkout", "admin"]
))
```

### Email Bots
**Agents:** Gmail automation, email marketing bots, support agents  
**Risks Blocked:** Bulk sending, forwarding all emails, exporting contacts  
**Example:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="email-bot",
    blocked_actions=["send_bulk", "forward_all", "export_contacts"],
    spending_limit=100.0
))
```

### Trading Bots
**Agents:** Crypto trading bots, stock trading agents, DeFi automation  
**Risks Blocked:** High-value transfers, unauthorized withdrawals  
**Example:**
```python
fence = RuntimeFence(FenceConfig(
    agent_id="trading-bot",
    blocked_actions=["withdraw", "transfer"],
    spending_limit=1000.0,
    blocked_targets=["wallet_private_key"]
))
```

### LangChain Agents
**Any LangChain agent with tools**  
**Full integration example:** See [langchain_integration.py](packages/python/langchain_integration.py)  
```python
from langchain_integration import create_fenced_agent, Preset

agent = create_fenced_agent(
    preset=Preset.CODING_ASSISTANT,
    agent_id="langchain-coder"
)
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Your AI Agent                        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   RUNTIME FENCE                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Validator   │  │ Risk Scorer │  │ Kill Switch │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Audit Log   │  │ Alerts      │  │ Settings    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼ (if allowed)
┌─────────────────────────────────────────────────────────┐
│                   External World                         │
│         (APIs, Files, Databases, Network)               │
└─────────────────────────────────────────────────────────┘
```

---

## 🔌 API Reference

### Python API

```python
from runtime_fence import RuntimeFence, FenceConfig, RiskLevel

# Initialize
fence = RuntimeFence(FenceConfig(
    agent_id="my-agent",
    blocked_actions=["delete"],
    spending_limit=100.0
))

# Validate actions
result = fence.validate(action="delete", target="file.txt")
print(result.allowed)      # False
print(result.risk_score)   # 50
print(result.reasons)      # ["Action 'delete' is blocked"]

# Kill switch
fence.kill("Emergency stop")

# Resume operations
fence.resume()

# Get status
status = fence.get_status()
print(status.is_killed)    # True/False
print(status.total_validations)  # Count
```

### CLI Commands

```bash
fence test               # Run safety tests
fence status             # Show fence status  
fence version            # Display version
```

For REST API documentation (coming soon), see [API-Reference.md](docs/API-Reference.md).

---

## ⚙️ Configuration

### Environment Variables (Optional)

```bash
# Agent identification
FENCE_AGENT_ID=my-agent

# Logging
FENCE_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Configuration via Code

```python
from runtime_fence import RuntimeFence, FenceConfig, RiskLevel

config = FenceConfig(
    agent_id="my-agent",
    blocked_actions=["delete", "exec"],
    blocked_targets=[".env", "production"],
    spending_limit=100.0,
    risk_threshold=RiskLevel.MEDIUM,  # LOW, MEDIUM, HIGH, CRITICAL
    auto_kill_on_critical=True,
    offline_mode=True
)

fence = RuntimeFence(config)
```

---

## 🛠️ Development

```bash
# Clone repo
git clone https://github.com/RunTimeAdmin/runtime-fence-ai.git
cd runtime-fence-ai/packages/python

# Install in development mode
pip install -e .

# Run tests
fence test
```

For detailed integration guides, see:
- [LangChain Integration](docs/Integration-Guide.md#langchain)
- [AutoGPT Integration](docs/Integration-Guide.md#autogpt)
- [Custom Agent Integration](docs/Integration-Guide.md#custom-agents)

---

## 📁 Project Structure

```
runtime-fence-ai/
├── packages/
│   └── python/              # Runtime Fence Python package
│       ├── runtime_fence.py # Core safety engine
│       ├── cli.py           # Command-line interface
│       └── langchain_integration.py  # LangChain helpers
├── docs/                    # Integration guides
│   ├── Integration-Guide.md
│   └── Troubleshooting-FAQ.md
└── wiki/                    # Documentation
    ├── Quick-Start.md
    └── Configuration.md
```

---

## 🌐 About

Built by **RunTimeAdmin** | David Cooper | CCIE #14019

**Why Runtime Fence Matters:**

As AI agents become more autonomous, the risk of unintended actions increases exponentially. Runtime Fence provides the safety layer that:
- Prevents agents from deleting critical files
- Blocks unauthorized API calls
- Limits spending and resource usage
- Provides complete audit trails
- Enables instant emergency shutdowns

**Use Cases:**
- Coding assistants that modify your codebase
- Autonomous agents with system access
- Data processing agents handling sensitive information
- Web automation with payment capabilities
- Any AI agent that needs guardrails

---

## 🔗 Links

- **GitHub:** [github.com/RunTimeAdmin/runtime-fence-ai](https://github.com/RunTimeAdmin/runtime-fence-ai)
- **PyPI Package:** [pypi.org/project/runtime-fence](https://pypi.org/project/runtime-fence)
- **Documentation:** [GitHub Wiki](https://github.com/RunTimeAdmin/runtime-fence-ai/wiki)
- **Issues:** [Report bugs or request features](https://github.com/RunTimeAdmin/runtime-fence-ai/issues)
- **Twitter:** [@protocol14019](https://x.com/protocol14019)

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

## ⚡ Quick Demo

### Stop a Coding Assistant from Deleting Files
```python
from runtime_fence import RuntimeFence, FenceConfig

fence = RuntimeFence(FenceConfig(
    agent_id="cursor-assistant",
    blocked_actions=["delete", "rm"]
))

result = fence.validate("delete", "important_code.py")
# Returns: {"allowed": False, "reasons": ["Action 'delete' is blocked"]}
```

### Protect Autonomous Agents from Self-Modification
```python
fence = RuntimeFence(FenceConfig(
    agent_id="autogpt",
    blocked_actions=["modify_self", "spawn_agent"]
))

result = fence.validate("modify_self", "autogpt_config.json")
# Returns: {"allowed": False, "risk_score": 85, "reasons": ["Action 'modify_self' is blocked"]}
```

### Block Data Agents from Exporting PII
```python
fence = RuntimeFence(FenceConfig(
    agent_id="data-analyst",
    blocked_actions=["export_pii"],
    blocked_targets=["customer_emails", "ssn"]
))

result = fence.validate("export", "customer_emails.csv")
# Returns: {"allowed": False, "reasons": ["Target 'customer_emails' is blocked"]}
```

### Emergency Stop ANY Agent
```python
fence.kill("Suspicious behavior detected")
# All agent operations halted immediately across ALL agents
```

---

**🛡️ Protect ANY AI Agent. Before it's too late.**

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📊 Status

**Core Features (Production Ready):**
- [x] Kill switch engine (sub-100ms response)
- [x] Python SDK (`pip install runtime-fence`)
- [x] Action blocking & target protection
- [x] Risk scoring & audit logging
- [x] CLI tools (`fence test`, `fence status`)
- [x] Offline mode (no API required)
- [x] LangChain integration

**Coming Soon:**
- [ ] TypeScript SDK
- [ ] Web dashboard
- [ ] REST API service
- [ ] Mobile app

---

## 🎯 Roadmap

### Now: Core Safety (Q1 2025)
- ✅ Python package on PyPI
- ✅ Universal agent support
- ✅ Offline-first architecture
- 🚧 TypeScript/JavaScript SDK

### Next: Integrations (Q2 2025)
- LangSmith integration
- CrewAI native support
- Anthropic Claude tools
- OpenAI Assistants API

### Future: Enterprise (Q3 2025)
- Multi-agent orchestration
- Centralized dashboard
- Team collaboration
- Advanced analytics

---

## 🔗 Links

- **GitHub:** [github.com/RunTimeAdmin/runtime-fence-ai](https://github.com/RunTimeAdmin/runtime-fence-ai)
- **PyPI Package:** [pypi.org/project/runtime-fence](https://pypi.org/project/runtime-fence)
- **Documentation:** [GitHub Wiki](https://github.com/RunTimeAdmin/runtime-fence-ai/wiki)
- **Issues:** [Report bugs or request features](https://github.com/RunTimeAdmin/runtime-fence-ai/issues)
- **Twitter:** [@protocol14019](https://x.com/protocol14019)

---

**🛡️ Runtime Fence - Because every AI needs an off switch.**
