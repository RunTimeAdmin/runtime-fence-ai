# Troubleshooting & FAQ

Common issues, solutions, and frequently asked questions for $KILLSWITCH.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Authentication Issues](#authentication-issues)
3. [Runtime Errors](#runtime-errors)
4. [Performance Issues](#performance-issues)
5. [Integration Problems](#integration-problems)
6. [FAQ](#faq)

---

## Installation Issues

### Python package won't install

**Error:**
```
ERROR: Could not find a version that satisfies the requirement killswitch-agent
```

**Solution:**
```bash
# Ensure Python 3.11+
python --version

# Upgrade pip
pip install --upgrade pip

# Install from source
git clone https://github.com/RunTimeAdmin/ai-agent-killswitch.git
cd ai-agent-killswitch/packages/python
pip install -e .
```

---

### Node.js dependency conflicts

**Error:**
```
npm ERR! ERESOLVE unable to resolve dependency tree
```

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and lock file
rm -rf node_modules package-lock.json

# Install with legacy peer deps
npm install --legacy-peer-deps
```

---

### Windows installer fails

**Error:**
```
'fence' is not recognized as an internal or external command
```

**Solution:**
1. Run installer as Administrator
2. Add to PATH manually:
   ```batch
   setx PATH "%PATH%;%LOCALAPPDATA%\Programs\killswitch"
   ```
3. Restart terminal

---

### Mac/Linux permission denied

**Error:**
```
./install_fence.sh: Permission denied
```

**Solution:**
```bash
chmod +x install_fence.sh
./install_fence.sh

# If still failing
sudo ./install_fence.sh
```

---

## Authentication Issues

### Invalid API key

**Error:**
```json
{"error": {"code": "INVALID_API_KEY", "message": "API key is invalid or expired"}}
```

**Solutions:**
1. Verify key format: `ks_live_xxxxx` or `ks_test_xxxxx`
2. Check environment variable:
   ```bash
   echo $KILLSWITCH_API_KEY
   ```
3. Regenerate key in dashboard at `/settings`

---

### JWT token expired

**Error:**
```json
{"error": {"code": "TOKEN_EXPIRED", "message": "JWT token has expired"}}
```

**Solution:**
```python
# Refresh token before expiry
from killswitch import Client

client = Client(api_key="ks_live_xxxxx")

# Auto-refresh is built in, but you can force it:
client.refresh_token()
```

---

### CORS errors in browser

**Error:**
```
Access to fetch at 'https://api.runtimefence.com' has been blocked by CORS policy
```

**Solution:**
- Use backend proxy for API calls
- Or use the SDK which handles CORS:
  ```typescript
  import { KillSwitch } from '@killswitch/sdk';
  const client = new KillSwitch({ apiKey: 'ks_live_xxxxx' });
  ```

---

## Runtime Errors

### Action blocked unexpectedly

**Error:**
```
BlockedError: Action 'file_read' was blocked. Reasons: ['Target matches blocked pattern']
```

**Diagnosis:**
```python
from killswitch import fence

# Check what's blocked
result = fence.validate("file_read", "/path/to/file")
print(f"Allowed: {result.allowed}")
print(f"Risk score: {result.risk_score}")
print(f"Reasons: {result.reasons}")
print(f"Matched rules: {result.matched_rules}")
```

**Solutions:**
1. Check blocked patterns in settings
2. Add exception for specific target:
   ```python
   fence.add_exception("file_read", "/path/to/safe/file")
   ```

---

### Agent killed unexpectedly

**Error:**
```
AgentKilledError: Agent 'my-agent' was killed. Reason: 'Anomaly score exceeded threshold'
```

**Diagnosis:**
```python
# Check agent status
status = fence.status("my-agent")
print(f"Status: {status}")
print(f"Kill reason: {status.kill_reason}")
print(f"Last actions: {status.recent_actions}")
```

**Solutions:**
1. Adjust thresholds:
   ```python
   fence.config.auto_kill_threshold = 95  # Higher = less sensitive
   ```
2. Review audit logs for trigger:
   ```python
   logs = fence.get_audit_logs(agent_id="my-agent", limit=10)
   for log in logs:
       print(f"{log.timestamp}: {log.action} -> {log.target} (risk: {log.risk_score})")
   ```

---

### Connection timeout

**Error:**
```
TimeoutError: Request to validation API timed out after 5000ms
```

**Solutions:**
1. Increase timeout:
   ```python
   fence.config.timeout_ms = 10000
   ```
2. Use fail-mode for resilience:
   ```python
   fence.config.fail_mode = "CACHED"  # Use last known policy
   ```
3. Check network connectivity

---

### Rate limit exceeded

**Error:**
```json
{"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}}
```

**Solutions:**
1. Implement backoff:
   ```python
   import time
   from killswitch import fence, RateLimitError
   
   try:
       result = fence.validate(action, target)
   except RateLimitError as e:
       time.sleep(e.retry_after)
       result = fence.validate(action, target)
   ```
2. Upgrade subscription tier for higher limits
3. Enable local caching:
   ```python
   fence.config.cache_validations = True
   fence.config.cache_ttl_seconds = 60
   ```

---

## Performance Issues

### Slow validation response

**Symptoms:** Validation takes >500ms

**Solutions:**
1. Enable local caching:
   ```python
   fence.config.cache_validations = True
   ```
2. Use batch validation:
   ```python
   results = fence.validate_batch([
       {"action": "read", "target": "file1.txt"},
       {"action": "read", "target": "file2.txt"},
   ])
   ```
3. Skip low-risk actions:
   ```python
   fence.config.skip_validation_threshold = 10  # Skip if risk < 10
   ```

---

### High memory usage

**Symptoms:** Python process using >1GB RAM

**Solutions:**
1. Limit audit log retention:
   ```python
   fence.config.local_audit_max_entries = 1000
   ```
2. Disable local caching:
   ```python
   fence.config.cache_validations = False
   ```
3. Use streaming for large operations:
   ```python
   for log in fence.stream_audit_logs():
       process(log)
   ```

---

### Desktop app consuming CPU

**Symptoms:** System tray app using >10% CPU

**Solutions:**
1. Reduce polling frequency:
   ```
   Settings > Advanced > Poll Interval: 5000ms
   ```
2. Disable real-time monitoring for idle agents
3. Check for stuck processes:
   ```bash
   # Linux/Mac
   ps aux | grep killswitch
   
   # Windows
   tasklist | findstr killswitch
   ```

---

## Integration Problems

### LangChain callback not firing

**Problem:** KillSwitchCallbackHandler not intercepting calls

**Solution:**
```python
from langchain.callbacks.manager import CallbackManager
from killswitch.integrations.langchain import KillSwitchCallbackHandler

# Create callback handler
ks_callback = KillSwitchCallbackHandler(agent_id="langchain")

# Attach via CallbackManager
callback_manager = CallbackManager([ks_callback])

# Pass to LLM
llm = OpenAI(callback_manager=callback_manager)
```

---

### OpenAI function calls not protected

**Problem:** Function calling bypasses fence

**Solution:**
```python
# Wrap the function execution, not the API call
@fence.wrap_function("function_call", "openai_functions")
def execute_function(name: str, args: dict):
    if name == "get_weather":
        return get_weather(**args)
    # ... etc
```

---

### AutoGPT ignoring kill signal

**Problem:** AutoGPT continues after kill

**Solution:**
1. Use hard kill with network isolation:
   ```python
   fence.kill("my-agent", hard=True, network_isolate=True)
   ```
2. Enable process-level kill:
   ```python
   fence.config.process_kill_enabled = True
   ```

---

## FAQ

### General Questions

**Q: What happens when the API is down?**

A: Depends on your `fail_mode` setting:
- `CLOSED` (default): All actions blocked
- `CACHED`: Uses last known policy
- `OPEN`: All actions allowed (NOT recommended)

---

**Q: Can agents bypass the fence?**

A: The fence includes multiple anti-bypass protections:
- Package integrity verification (SHA-256)
- Runtime tamper detection
- Process isolation support
- Network-level kill switch

See [Security Hardening](Security-Hardening.md) for details.

---

**Q: How fast is the kill switch?**

A: Under normal conditions:
- API kill signal: <100ms
- SPIFFE revocation propagation: <30 seconds
- Network-level isolation: <1 second
- Process termination: <3 seconds (SIGTERM → SIGKILL)

---

**Q: Is my data stored?**

A: We store:
- Agent registration info
- Audit logs (retained per your subscription tier)
- Settings and preferences

We DO NOT store:
- Action payloads
- File contents
- API responses

---

### Token Questions

**Q: Do I need $KILLSWITCH tokens to use the service?**

A: No. The service works with USD subscriptions. Tokens provide optional benefits:
- Subscription discounts (10-40%)
- Governance voting rights
- Priority support access

---

**Q: How do token discounts work?**

A: Hold tokens in your connected wallet:
- 10,000+ tokens = 10% discount
- 100,000+ tokens = 20% discount
- 1,000,000+ tokens = 40% discount

Discount applied automatically at checkout.

---

### Security Questions

**Q: What if my API key is leaked?**

A: Immediately:
1. Rotate key in dashboard: `/settings` → API Keys → Regenerate
2. Kill all agents: `POST /api/runtime/kill` with `scope: "all"`
3. Review audit logs for unauthorized access

---

**Q: Can I use this in production?**

A: Yes. The platform is production-ready:
- 82 tests passing
- SPIFFE/SPIRE identity integration
- SOC2/ISO 27001 compliance ready
- <100ms latency
- 99.9% uptime SLA (Enterprise tier)

---

**Q: Is the code audited?**

A: Self-audit completed. Professional third-party audit planned for Q2 2026. See [SELF_AUDIT_REPORT.md](SELF_AUDIT_REPORT.md).

---

### Billing Questions

**Q: What happens if I exceed my tier limits?**

A: Depends on the limit:
- **Agents**: New registrations blocked, existing agents work
- **Actions/day**: Validation returns cached results or blocks (per fail_mode)
- **API requests**: 429 rate limit response

Upgrade at any time; changes apply immediately.

---

**Q: Can I get a refund?**

A: Yes. 14-day money-back guarantee on all subscription tiers. Contact support@runtimefence.com.

---

## Still Need Help?

- **Discord:** [discord.gg/killswitch](https://discord.gg/killswitch)
- **Email:** support@runtimefence.com
- **GitHub Issues:** [Create an issue](https://github.com/RunTimeAdmin/ai-agent-killswitch/issues)

---

## Related Documentation

- [API Reference](API-Reference.md)
- [Integration Guide](Integration-Guide.md)
- [Security Hardening](Security-Hardening.md)
