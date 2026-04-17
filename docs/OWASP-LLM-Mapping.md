# OWASP Top 10 for LLM Applications — Runtime Fence Mapping

This document maps the [OWASP Top 10 for LLM Applications (2025)](https://owasp.org/www-project-top-10-for-large-language-model-applications/) to Runtime Fence's security controls.

| # | OWASP LLM Risk | Runtime Fence Mitigation | Module | Status |
|---|----------------|--------------------------|--------|--------|
| LLM01 | **Prompt Injection** | Intent analysis detects obfuscated commands (base64, chr(), eval/exec patterns). Pre-filter + LLM shadow analysis. | `intent_analyzer.py` | ✅ Implemented |
| LLM02 | **Insecure Output Handling** | Action validation blocks dangerous outputs (file_delete, network_access, code_execution). Configurable blocked_actions list. | `runtime_fence.py` | ✅ Implemented |
| LLM03 | **Training Data Poisoning** | Tamper detection via SHA-256 hash verification of all security modules. Build-time frozen hashes. | `bypass_protection.py` | ✅ Implemented |
| LLM04 | **Model Denial of Service** | Rate limiting in `validate()` (100 calls/sec/agent). Sliding window detects sustained abuse. | `runtime_fence.py`, `sliding_window.py` | ✅ Implemented |
| LLM05 | **Supply Chain Vulnerabilities** | Package integrity verification via `HashManifest`. Runtime tamper detection blocks module reloading. Protected `__import__` hook. | `bypass_protection.py` | ✅ Implemented |
| LLM06 | **Sensitive Information Disclosure** | Exfiltration detection tracks unique data targets per agent. Behavioral thresholds trigger kill on mass data access. | `behavioral_thresholds.py` | ✅ Implemented |
| LLM07 | **Insecure Plugin Design** | `FencedTool` wrapper validates all LangChain tool calls through RuntimeFence before execution. Callback handler intercepts tool starts. | `langchain_integration.py` | ✅ Implemented |
| LLM08 | **Excessive Agency** | Task adherence (cosine similarity drift detection), spending limits, action/target blocklists. Kill switch on drift threshold. | `task_adherence.py`, `runtime_fence.py` | ✅ Implemented |
| LLM09 | **Overreliance** | Governance separation requires human vote/approval for high-impact actions. LOCAL vs GOVERNED action routing. | `governance_separation.py` | ✅ Implemented |
| LLM10 | **Model Theft** | Network kill blocks agent egress at OS firewall level. Per-process/per-user isolation. Read-only enforcement prevents model file copying. | `network_kill.py`, `bypass_protection.py` | ✅ Implemented |

## Defense-in-Depth Architecture

Runtime Fence implements a layered defense model:

1. **Pre-execution** — Intent analysis, action blocking, task adherence check
2. **During execution** — Behavioral monitoring, sliding window detection, spending limits
3. **Post-detection** — Hard kill (SIGTERM→SIGKILL), network kill (firewall), governance escalation
4. **Forensics** — Immutable audit logs (hash-chained), honeypot evidence collection, breach history

## Additional Controls Not in OWASP Top 10

| Control | Module | Description |
|---------|--------|-------------|
| Kill Switch | `hard_kill.py` | Process-group termination with cross-platform support |
| Network Isolation | `network_kill.py` | OS-level firewall containment (iptables/pf/netsh) |
| Honeypot Detection | `realistic_honeypot.py` | Deceptive sandbox with forensic evidence collection |
| Fail-Mode Strategy | `fail_mode.py` | CLOSED/CACHED/OPEN degradation when API unavailable |
| SPIFFE Identity | `spiffe.py` | Workload API integration for agent authentication |
