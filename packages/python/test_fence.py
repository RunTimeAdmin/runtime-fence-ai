"""
Simple Fence Test - No API required
"""
from runtime_fence import RuntimeFence, FenceConfig, FencedAgent, RiskLevel

# Create fence with NO API connection (offline mode)
config = FenceConfig(
    agent_id="test-bot",
    api_url="http://localhost:9999",  # Won't connect - that's OK
    spending_limit=500.0,
    blocked_actions=["delete", "withdraw_all"],
    blocked_targets=["evil-wallet", "suspicious.com"],
    risk_threshold=RiskLevel.HIGH,
    auto_kill_on_critical=False  # Don't auto-kill for testing
)

fence = RuntimeFence(config)

print("=== Runtime Fence Test ===\n")

# Test 1: Normal action - should PASS
print("Test 1: Normal buy action")
result = fence.validate("buy", "BTC", amount=100.0)
print(f"  Allowed: {result.allowed}")
print(f"  Risk: {result.risk_score}%\n")

# Test 2: Blocked action - should FAIL
print("Test 2: Blocked action (delete)")
result = fence.validate("delete", "database", amount=0)
print(f"  Allowed: {result.allowed}")
print(f"  Risk: {result.risk_score}%")
print(f"  Reason: {result.reasons}\n")

# Test 3: Blocked target - should FAIL
print("Test 3: Blocked target (evil-wallet)")
result = fence.validate("transfer", "evil-wallet", amount=50.0)
print(f"  Allowed: {result.allowed}")
print(f"  Risk: {result.risk_score}%")
print(f"  Reason: {result.reasons}\n")

# Test 4: Exceeds spending limit - should FAIL
print("Test 4: Exceeds spending limit ($600 > $500)")
result = fence.validate("buy", "ETH", amount=600.0)
print(f"  Allowed: {result.allowed}")
print(f"  Risk: {result.risk_score}%")
print(f"  Reason: {result.reasons}\n")

# Test 5: Multiple transactions tracking
print("Test 5: Spending accumulation")
fence.validate("buy", "BTC", amount=200.0)  # $200 spent
fence.validate("buy", "ETH", amount=200.0)  # $400 total
result = fence.validate("buy", "SOL", amount=200.0)  # $600 total - over limit!
print(f"  Allowed: {result.allowed}")
print(f"  Total spent: ${fence.total_spent}")
print(f"  Reason: {result.reasons}\n")

# Test 6: Manual kill switch
print("Test 6: Manual kill switch")
fence.kill("Testing emergency stop")
result = fence.validate("buy", "DOGE", amount=1.0)
print(f"  Allowed: {result.allowed}")
print(f"  Reason: {result.reasons}\n")

# Final status
print("=== Final Fence Status ===")
status = fence.get_status()
for key, value in status.items():
    print(f"  {key}: {value}")
