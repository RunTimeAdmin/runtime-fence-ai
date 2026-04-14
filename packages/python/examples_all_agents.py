"""
Runtime Fence Examples for Common AI Bot Types
"""
from runtime_fence import RuntimeFence, FenceConfig, FencedAgent, RiskLevel


# =====================================================
# 1. CODING ASSISTANT (like Copilot, Cursor, Aider)
# =====================================================

coding_fence = RuntimeFence(FenceConfig(
    agent_id="coding-assistant",
    offline_mode=True,  # Local validation only
    blocked_actions=[
        "exec",           # No executing arbitrary code
        "shell",          # No shell commands
        "rm",             # No file deletion
        "sudo",           # No privilege escalation
        "install",        # No installing packages without approval
        "push",           # No git push without review
        "deploy",         # No deployments
    ],
    blocked_targets=[
        ".env",           # No touching secrets
        ".ssh",           # No SSH keys
        "node_modules",   # No modifying dependencies
        "/etc",           # No system files
        "credentials",    # No credential files
        "password",       # No password files
    ],
    spending_limit=0,  # No spending
    risk_threshold=RiskLevel.MEDIUM
))

print("=== Coding Assistant Fence ===")
print(coding_fence.validate("read", "src/app.py"))      # OK
print(coding_fence.validate("write", "src/app.py"))     # OK
print(coding_fence.validate("exec", "rm -rf /"))        # BLOCKED
print(coding_fence.validate("read", ".env"))            # BLOCKED


# =====================================================
# 2. EMAIL/COMMUNICATION BOT
# =====================================================

email_fence = RuntimeFence(FenceConfig(
    agent_id="email-bot",
    offline_mode=True,
    blocked_actions=[
        "send_bulk",      # No mass emails
        "forward_all",    # No forwarding everything
        "delete_all",     # No mass deletion
        "export",         # No exporting contact lists
        "share_external", # No sharing outside org
        "auto_reply_all", # No auto-replying to everyone
    ],
    blocked_targets=[
        "all_contacts",   # No accessing full contact list
        "external",       # No external domains by default
        "spam",           # No spam folders
        "admin@",         # No impersonating admin
    ],
    spending_limit=100,  # Max 100 emails per session
    risk_threshold=RiskLevel.MEDIUM
))

print("\n=== Email Bot Fence ===")
print(email_fence.validate("send", "user@company.com", amount=1))   # OK
print(email_fence.validate("send_bulk", "all_contacts", amount=1000)) # BLOCKED
print(email_fence.validate("read", "inbox"))                         # OK


# =====================================================
# 3. DATA ANALYSIS BOT
# =====================================================

data_fence = RuntimeFence(FenceConfig(
    agent_id="data-analyst",
    offline_mode=True,
    blocked_actions=[
        "delete",         # No deleting data
        "drop_table",     # No dropping tables
        "truncate",       # No truncating
        "export_pii",     # No exporting personal data
        "share",          # No sharing raw data
        "modify_schema",  # No schema changes
    ],
    blocked_targets=[
        "production",     # No production database
        "pii_table",      # No PII tables
        "financial",      # No financial data
        "passwords",      # No password tables
        "audit_log",      # No modifying audit logs
    ],
    spending_limit=1000000,  # Max 1M rows queried
    risk_threshold=RiskLevel.HIGH
))

print("\n=== Data Analysis Fence ===")
print(data_fence.validate("select", "analytics_table", amount=100))  # OK
print(data_fence.validate("delete", "production", amount=0))         # BLOCKED
print(data_fence.validate("export_pii", "users", amount=0))          # BLOCKED


# =====================================================
# 4. FILE MANAGEMENT BOT
# =====================================================

file_fence = RuntimeFence(FenceConfig(
    agent_id="file-manager",
    offline_mode=True,
    blocked_actions=[
        "delete",         # No deleting
        "move_external",  # No moving outside system
        "chmod",          # No permission changes
        "encrypt",        # No encrypting (ransomware risk)
        "upload_cloud",   # No uploading to external cloud
        "compress_all",   # No mass compression
    ],
    blocked_targets=[
        "system32",       # No system files
        "C:\\Windows",    # No Windows directory
        "/usr",           # No Unix system
        "/bin",           # No binaries
        ".git",           # No git internals
        "backup",         # No touching backups
    ],
    spending_limit=10000,  # Max 10GB operations
    risk_threshold=RiskLevel.MEDIUM
))

print("\n=== File Manager Fence ===")
print(file_fence.validate("read", "documents/report.pdf"))     # OK
print(file_fence.validate("copy", "documents/", amount=100))   # OK
print(file_fence.validate("delete", "system32", amount=0))     # BLOCKED


# =====================================================
# 5. WEB BROWSING/SCRAPING BOT
# =====================================================

web_fence = RuntimeFence(FenceConfig(
    agent_id="web-browser",
    offline_mode=True,
    blocked_actions=[
        "submit_form",    # No form submissions
        "login",          # No logging into sites
        "purchase",       # No purchases
        "download_exe",   # No downloading executables
        "click_ad",       # No clicking ads
        "post",           # No posting content
    ],
    blocked_targets=[
        "banking",        # No banking sites
        "payment",        # No payment processors
        "admin",          # No admin panels
        ".exe",           # No executables
        "darkweb",        # No dark web
        "malware",        # No malware sites
    ],
    spending_limit=0,     # No spending allowed
    risk_threshold=RiskLevel.MEDIUM
))

print("\n=== Web Browser Fence ===")
print(web_fence.validate("browse", "wikipedia.org"))          # OK
print(web_fence.validate("scrape", "news-site.com"))          # OK
print(web_fence.validate("login", "banking.com"))             # BLOCKED
print(web_fence.validate("purchase", "amazon.com", amount=50)) # BLOCKED


# =====================================================
# 6. CUSTOMER SERVICE BOT
# =====================================================

support_fence = RuntimeFence(FenceConfig(
    agent_id="support-bot",
    offline_mode=True,
    blocked_actions=[
        "refund",         # No issuing refunds
        "cancel_account", # No canceling accounts
        "change_plan",    # No plan changes
        "access_payment", # No payment info access
        "escalate_all",   # No mass escalation
        "close_ticket",   # No closing without resolution
    ],
    blocked_targets=[
        "billing",        # No billing system
        "admin_panel",    # No admin access
        "user_passwords", # No password access
        "internal_docs",  # No internal documentation
        "competitor",     # No competitor mentions
    ],
    spending_limit=100,   # Max $100 in credits/discounts
    risk_threshold=RiskLevel.HIGH
))

print("\n=== Customer Service Fence ===")
print(support_fence.validate("respond", "ticket-123"))          # OK
print(support_fence.validate("lookup", "order-456"))            # OK
print(support_fence.validate("refund", "order-456", amount=500)) # BLOCKED (over limit)
print(support_fence.validate("access_payment", "user-789"))     # BLOCKED


# =====================================================
# 7. AUTONOMOUS AGENT (AutoGPT, BabyAGI style)
# =====================================================

auto_fence = RuntimeFence(FenceConfig(
    agent_id="autonomous-agent",
    offline_mode=True,
    blocked_actions=[
        "spawn_agent",    # No creating more agents
        "modify_self",    # No self-modification
        "access_internet",# Limited internet (except allowed)
        "execute_code",   # No arbitrary code
        "create_file",    # Limited file creation
        "send_request",   # Limited API calls
        "purchase",       # No purchasing
        "sign_contract",  # No legal agreements
    ],
    blocked_targets=[
        "api_keys",       # No API key access
        "wallets",        # No crypto wallets
        "bank",           # No banking
        "social_media",   # No social media posting
        "email",          # No email sending
        "production",     # No production systems
    ],
    spending_limit=10,    # Very low spending limit
    risk_threshold=RiskLevel.LOW,  # Very strict
    auto_kill_on_critical=True
))

print("\n=== Autonomous Agent Fence ===")
print(auto_fence.validate("think", "planning"))              # OK
print(auto_fence.validate("read", "local-file.txt"))         # OK
print(auto_fence.validate("spawn_agent", "helper"))          # BLOCKED
print(auto_fence.validate("access_internet", "api.openai.com")) # BLOCKED


# =====================================================
# SUMMARY: How to use for YOUR agent
# =====================================================
"""
To wrap YOUR AI agent:

1. Identify risky actions your agent can take
2. Identify sensitive targets it might access
3. Set spending/rate limits if applicable
4. Choose risk threshold (LOW=strict, HIGH=lenient)

Example for a custom agent:

my_fence = RuntimeFence(FenceConfig(
    agent_id="my-custom-agent",
    blocked_actions=["action1", "action2"],
    blocked_targets=["target1", "target2"],
    spending_limit=100,
    risk_threshold=RiskLevel.MEDIUM
))

# Wrap any function
@my_fence.wrap_function("action_name", "target")
def my_agent_function():
    pass

# Or validate manually
result = my_fence.validate("action", "target", amount=0)
if result.allowed:
    do_the_thing()
else:
    print(f"Blocked: {result.reasons}")
"""

if __name__ == "__main__":
    print("\n" + "="*50)
    print("All fence examples completed!")
    print("="*50)
