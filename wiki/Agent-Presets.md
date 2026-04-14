# Agent Presets

Pre-configured $KILLSWITCH settings for common AI agent types.

## Available Presets

### Coding Assistant
For AI coding tools like GitHub Copilot, Cursor, Aider.

**Blocked Actions:**
- `exec` - Execute arbitrary code
- `shell` - Shell commands
- `rm` - Delete files
- `sudo` - Elevated privileges
- `chmod` - Change permissions

**Blocked Targets:**
- `.env` - Environment files
- `.ssh` - SSH keys
- `node_modules` - Dependencies

**Best For:** Copilot, Cursor, Cody, Aider, Continue

---

### Email Bot
For email automation agents.

**Blocked Actions:**
- `send_bulk` - Mass email
- `forward_all` - Forward entire inbox
- `delete_all` - Delete all emails
- `export_contacts` - Export contact list

**Blocked Targets:**
- `all_contacts` - Full contact list
- `credentials` - Login info
- `payment_info` - Payment data

**Best For:** Email assistants, inbox managers, auto-responders

---

### Data Analyst
For data processing and analysis agents.

**Blocked Actions:**
- `delete` - Delete data
- `drop_table` - Drop database tables
- `truncate` - Clear tables
- `export_pii` - Export personal data

**Blocked Targets:**
- `production` - Production database
- `pii_data` - Personal data
- `financial` - Financial records

**Best For:** Data analysis agents, ETL pipelines, report generators

---

### Web Browser
For web scraping and automation agents.

**Blocked Actions:**
- `login` - Auto-login
- `purchase` - Make purchases
- `submit_form` - Submit forms
- `download_exe` - Download executables

**Blocked Targets:**
- `bank` - Banking sites
- `admin` - Admin panels
- `payment` - Payment pages

**Best For:** Web scrapers, browser automation, research agents

---

### Autonomous Agent
Maximum restrictions for self-directed agents like AutoGPT.

**Blocked Actions:**
- `spawn_agent` - Create new agents
- `modify_self` - Self-modification
- `execute_code` - Run code
- `network_request` - External network
- `file_write` - Write to disk

**Blocked Targets:**
- `system` - System files
- `config` - Configuration
- `credentials` - All credentials
- `agents` - Other agents

**Best For:** AutoGPT, BabyAGI, LangChain agents, CrewAI

---

## Using Presets

### In Code

```python
from runtime_fence import RuntimeFence, FenceConfig

# Use a preset
config = FenceConfig(
    agent_id="my-agent",
    preset="coding"  # Use coding assistant preset
)

fence = RuntimeFence(config)
```

### In Settings UI

1. Open `http://localhost:3000/settings`
2. Select a preset from the dropdown
3. Click "Apply Preset"
4. Optionally customize further
5. Click "Save"

### Via API

```bash
curl -X POST http://localhost:3001/api/settings \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"preset": "autonomous"}'
```

## Custom Presets

You can create custom presets by starting with a base preset and adding/removing items:

```python
config = FenceConfig(
    agent_id="my-custom-agent",
    preset="coding",  # Start with coding preset
    blocked_actions=["exec", "shell", "rm", "my_custom_action"],  # Add more
    blocked_targets=[".env", ".ssh", "my_sensitive_file"]  # Add more
)
```
