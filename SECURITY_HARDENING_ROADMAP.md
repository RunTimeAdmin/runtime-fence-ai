# Security Hardening Roadmap

**Source:** Network Security Analysis (CCIE Perspective)
**Status:** Technical Debt & Improvements
**Last Updated:** February 2, 2026

---

## Executive Summary

This document addresses security gaps identified in the $KILLSWITCH Runtime Fence implementation, moving from "cool tool" to "enterprise-grade."

---

## Current State Assessment

### What Works Well

| Component | Assessment |
|-----------|------------|
| Policy Enforcement Point (PEP) | ✅ RuntimeFence acts as gatekeeper |
| SDK/Decorator approach | ✅ `@fence.wrap_function` is fail-safe |
| Multi-tiered control | ✅ Action + Target + Cost coverage |
| Infrastructure breadth | ✅ Monorepo, SDKs, API, Desktop app |

### Identified Gaps

| Issue | Severity | Status |
|-------|----------|--------|
| Bypass Risk | **CRITICAL** | 🔴 Not addressed |
| Fail-Mode Strategy | **HIGH** | 🔴 Not defined |
| Secret Exposure | **MEDIUM** | 🟡 Needs cleanup |
| Intent Analysis | **HIGH** | 🔴 Keyword-only |
| Network-Level Kill | **HIGH** | 🔴 App-level only |
| Statefulness | **HIGH** | 🔴 Single-action only |
| Hard Kill (SIGKILL) | **MEDIUM** | 🟡 Soft signal only |

---

## Issue 1: Bypass Risk (CRITICAL)

### Problem
If the agent can modify its environment or the `runtime_fence` package itself, the kill switch is useless. "Living off the land" attack.

### Attack Vector
```python
# Malicious agent bypasses fence
import subprocess
subprocess.run(['pip', 'install', '--upgrade', 'runtime-fence==0.0.1-backdoor'])
# Or simply
import os
os.remove('/path/to/runtime_fence/validator.py')
```

### Mitigations

#### 1. Package Integrity Verification
```python
# fence_integrity.py
import hashlib
import sys

EXPECTED_HASHES = {
    'runtime_fence/__init__.py': 'sha256:abc123...',
    'runtime_fence/validator.py': 'sha256:def456...',
}

def verify_fence_integrity():
    """Verify runtime_fence hasn't been tampered with"""
    import runtime_fence
    package_path = runtime_fence.__path__[0]
    
    for file, expected_hash in EXPECTED_HASHES.items():
        filepath = f"{package_path}/{file}"
        with open(filepath, 'rb') as f:
            actual_hash = f'sha256:{hashlib.sha256(f.read()).hexdigest()}'
        
        if actual_hash != expected_hash:
            # CRITICAL: Fence compromised
            trigger_hard_kill()
            raise SecurityError(f"FENCE TAMPERED: {file}")

# Run on every fence initialization
verify_fence_integrity()
```

#### 2. Read-Only Installation
```bash
# Install fence as root, agent runs as non-root
sudo pip install runtime-fence
sudo chmod -R 555 /usr/local/lib/python3.10/site-packages/runtime_fence/
```

#### 3. Container Isolation
```yaml
# Run agent in container with read-only fence
securityContext:
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

---

## Issue 2: Fail-Mode Strategy (HIGH)

### Problem
If API validation is slow or unavailable, does agent:
- **Fail-Closed:** Hang/block (safe but disruptive)
- **Fail-Open:** Skip check (dangerous)

### Current Behavior
Undefined. Likely hangs on timeout.

### Solution: Explicit Fail-Mode Configuration

```python
# fence_config.py
class FailMode(Enum):
    CLOSED = "closed"  # Block on error (default for production)
    OPEN = "open"      # Allow on error (NEVER use in production)
    CACHED = "cached"  # Use last known policy (compromise)

class FenceConfig:
    fail_mode: FailMode = FailMode.CLOSED
    api_timeout_ms: int = 100  # Fast timeout
    cache_ttl_seconds: int = 60  # Cache policy for 60s
    
    @staticmethod
    def on_api_failure(action: str) -> bool:
        if FenceConfig.fail_mode == FailMode.CLOSED:
            log_critical(f"FAIL-CLOSED: Blocking {action} due to API failure")
            return False  # Block
        elif FenceConfig.fail_mode == FailMode.CACHED:
            return check_cached_policy(action)
        else:
            log_warning(f"FAIL-OPEN: Allowing {action} - DANGEROUS")
            return True  # Allow (dangerous)
```

### Implementation Priority
- **Production:** Always CLOSED
- **Development:** CACHED acceptable
- **OPEN:** Never (remove option entirely?)

---

## Issue 3: Secret Management (MEDIUM)

### Problem
`secret-scan-results.txt` in repo reveals patterns.

### Action Required
```bash
# Remove from repo
rm secret-scan-results.txt
echo "secret-scan-results.txt" >> .gitignore
git add .gitignore
git rm --cached secret-scan-results.txt
git commit -m "Remove secret scan results from repo"
```

### Best Practice
- Run scans in CI/CD, don't commit results
- Use pre-commit hooks to prevent secret commits

---

## Issue 4: Intent Analysis (HIGH)

### Problem
Keyword blocking is easily bypassed:
```python
# Blocked: subprocess.run(['rm', '-rf', '/'])
# Bypass: __import__('os').system(chr(114)+chr(109)+' -rf /')
```

### Solution: Shadow LLM Intent Analysis

```python
# intent_analyzer.py
from openai import OpenAI

class IntentAnalyzer:
    """Use small, cheap LLM to analyze intent before execution"""
    
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-4o-mini"  # Cheap, fast
    
    def analyze_intent(self, code: str) -> dict:
        """Analyze what the code is trying to do"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "system",
                "content": """Analyze this code and classify its intent:
                - file_delete: Deletes files
                - file_read: Reads files
                - network_request: Makes HTTP requests
                - shell_exec: Executes shell commands
                - data_exfil: Sends data to external server
                - privilege_escalation: Attempts to gain elevated access
                - benign: Safe operation
                
                Respond with JSON: {"intent": "category", "risk": 0-100, "reason": "..."}"""
            }, {
                "role": "user",
                "content": code
            }],
            max_tokens=100,
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    
    def should_block(self, code: str) -> tuple[bool, str]:
        """Determine if code should be blocked based on intent"""
        analysis = self.analyze_intent(code)
        
        HIGH_RISK_INTENTS = ['file_delete', 'data_exfil', 'privilege_escalation']
        
        if analysis['intent'] in HIGH_RISK_INTENTS:
            return True, f"Blocked: {analysis['intent']} - {analysis['reason']}"
        
        if analysis['risk'] > 70:
            return True, f"Blocked: Risk score {analysis['risk']}"
        
        return False, "Allowed"
```

### Trade-off
- **Latency:** +50-200ms per check
- **Cost:** ~$0.001 per check
- **Accuracy:** Much higher than keyword matching

---

## Issue 5: Network-Level Kill (HIGH)

### Problem
`fence.kill()` is app-level only. Agent can ignore soft signals.

### Solution: OS-Level Network Containment

```python
# network_kill.py
import subprocess
import platform

class NetworkKill:
    """Kill agent at network level, not just application level"""
    
    @staticmethod
    def kill_network_access(agent_pid: int = None):
        """Cut agent's internet access at OS level"""
        os_type = platform.system()
        
        if os_type == "Linux":
            # Add iptables rule to drop all traffic from agent
            if agent_pid:
                subprocess.run([
                    'iptables', '-A', 'OUTPUT',
                    '-m', 'owner', '--pid-owner', str(agent_pid),
                    '-j', 'DROP'
                ], check=True)
            else:
                # Nuclear option: drop all outbound
                subprocess.run(['iptables', '-P', 'OUTPUT', 'DROP'], check=True)
        
        elif os_type == "Darwin":  # macOS
            # Use pf firewall
            subprocess.run([
                'pfctl', '-t', 'blocked_agents', '-T', 'add', '0.0.0.0/0'
            ], check=True)
        
        elif os_type == "Windows":
            # Use Windows Firewall
            subprocess.run([
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name=KillSwitch_Block',
                'dir=out', 'action=block', 'enable=yes'
            ], check=True)
    
    @staticmethod
    def restore_network_access():
        """Restore network after safe state confirmed"""
        os_type = platform.system()
        
        if os_type == "Linux":
            subprocess.run(['iptables', '-F', 'OUTPUT'], check=True)
        elif os_type == "Darwin":
            subprocess.run(['pfctl', '-t', 'blocked_agents', '-T', 'flush'], check=True)
        elif os_type == "Windows":
            subprocess.run([
                'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                'name=KillSwitch_Block'
            ], check=True)
```

### Enterprise Integration
```python
# For VPC/cloud environments
def kill_vpc_access(agent_id: str):
    """Revoke security group access for agent"""
    import boto3
    ec2 = boto3.client('ec2')
    
    # Add deny rule to security group
    ec2.authorize_security_group_egress(
        GroupId='sg-agent-group',
        IpPermissions=[{
            'IpProtocol': '-1',  # All traffic
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
            'Description': f'KILLSWITCH: Block {agent_id}'
        }]
    )
```

---

## Issue 6: Statefulness (HIGH)

### Problem
Current validation looks at single actions. Can't detect:
- 10,000 file reads in 1 minute (data exfiltration)
- Gradual privilege escalation over time
- Coordinated multi-agent attacks

### Solution: Behavioral Thresholds

```python
# behavioral_fence.py
from collections import defaultdict
from datetime import datetime, timedelta

class BehavioralFence:
    """Track agent behavior over time, not just single actions"""
    
    def __init__(self):
        self.action_history = defaultdict(list)
        self.thresholds = {
            'file_read': {'count': 100, 'window_minutes': 1},
            'network_request': {'count': 50, 'window_minutes': 1},
            'shell_exec': {'count': 10, 'window_minutes': 5},
        }
    
    def record_action(self, agent_id: str, action_type: str):
        """Record action with timestamp"""
        self.action_history[f"{agent_id}:{action_type}"].append(datetime.now())
    
    def check_behavioral_threshold(self, agent_id: str, action_type: str) -> bool:
        """Check if agent is exceeding behavioral thresholds"""
        if action_type not in self.thresholds:
            return True  # No threshold defined
        
        threshold = self.thresholds[action_type]
        key = f"{agent_id}:{action_type}"
        window = timedelta(minutes=threshold['window_minutes'])
        cutoff = datetime.now() - window
        
        # Count recent actions
        recent_actions = [t for t in self.action_history[key] if t > cutoff]
        
        if len(recent_actions) >= threshold['count']:
            self.trigger_behavioral_alert(agent_id, action_type, len(recent_actions))
            return False  # Block
        
        return True  # Allow
    
    def trigger_behavioral_alert(self, agent_id: str, action_type: str, count: int):
        """Alert on suspicious behavior pattern"""
        log_critical(f"BEHAVIORAL ALERT: {agent_id} performed {count} {action_type} actions")
        # Auto-kill if threshold exceeded by 2x
        if count >= self.thresholds[action_type]['count'] * 2:
            trigger_auto_kill(agent_id, f"Behavioral threshold exceeded: {action_type}")
```

---

## Issue 7: Hard Kill - SIGKILL (MEDIUM)

### Problem
`fence.kill()` sends soft signal. Hung process may ignore it.

### Solution: Escalating Kill Strategy

```python
# hard_kill.py
import os
import signal
import time

def kill_agent(pid: int, escalate: bool = True):
    """Kill agent process with escalation"""
    
    # Step 1: Soft kill (SIGTERM)
    try:
        os.kill(pid, signal.SIGTERM)
        log_info(f"Sent SIGTERM to {pid}")
    except ProcessLookupError:
        return True  # Already dead
    
    if not escalate:
        return True
    
    # Step 2: Wait 2 seconds
    time.sleep(2)
    
    # Step 3: Check if still alive
    try:
        os.kill(pid, 0)  # Signal 0 = check existence
    except ProcessLookupError:
        return True  # Dead
    
    # Step 4: Hard kill (SIGKILL)
    log_warning(f"SIGTERM ignored, sending SIGKILL to {pid}")
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    
    # Step 5: Verify death
    time.sleep(0.5)
    try:
        os.kill(pid, 0)
        log_critical(f"SIGKILL FAILED for {pid} - zombie process?")
        return False
    except ProcessLookupError:
        log_info(f"Agent {pid} confirmed dead")
        return True
```

---

## Implementation Priority

| Issue | Effort | Impact | Priority |
|-------|--------|--------|----------|
| Fail-Mode Strategy | 2 hours | HIGH | **P1** |
| Hard Kill (SIGKILL) | 1 hour | MEDIUM | **P1** |
| Secret Cleanup | 30 min | MEDIUM | **P1** |
| Statefulness | 4 hours | HIGH | **P2** |
| Network-Level Kill | 4 hours | HIGH | **P2** |
| Bypass Protection | 8 hours | CRITICAL | **P2** |
| Intent Analysis | 8 hours | HIGH | **P3** |

---

## Compliance Angle (Enterprise Sales)

For banking/enterprise sector, emphasize:

1. **Audit Logging:** Every block logged with reason
2. **Non-Bypassability:** Package integrity verification
3. **Fail-Closed:** Defined behavior on failure
4. **Network Isolation:** OS-level, not app-level
5. **Behavioral Detection:** Exfiltration prevention

---

**Document Author:** Security Analysis Team
**Next Review:** Before Enterprise beta launch
