"""
Example: Wrapping an AI Trading Bot with Runtime Fence
"""

from runtime_fence import create_fence, FencedAgent, FenceConfig, RiskLevel, RuntimeFence


# ======================
# EXAMPLE 1: Simple wrapper
# ======================

# Create the fence
fence = create_fence(
    agent_id="trading-bot-001",
    api_url="http://localhost:3001",
    spending_limit=500.0
)

# Now wrap any function
@fence.wrap_function("transfer", "bank_api")
def transfer_money(to_account: str, amount: float):
    """This function is now protected by the fence."""
    print(f"Transferring ${amount} to {to_account}")
    return {"status": "success", "amount": amount}


# Try it - will be validated first
try:
    transfer_money("account-123", amount=100.0)  # Allowed
    transfer_money("account-456", amount=600.0)  # Blocked - exceeds limit
except PermissionError as e:
    print(f"Blocked: {e}")


# ======================
# EXAMPLE 2: Full agent class
# ======================

class TradingBot(FencedAgent):
    """A trading bot that operates through the fence."""
    
    def __init__(self, fence):
        super().__init__(fence)
        self.portfolio = {}
    
    def _do_action(self, action: str, target: str, amount: float, **kwargs):
        """Execute the actual trading action."""
        if action == "buy":
            self.portfolio[target] = self.portfolio.get(target, 0) + amount
            return {"bought": target, "amount": amount}
        
        elif action == "sell":
            if self.portfolio.get(target, 0) >= amount:
                self.portfolio[target] -= amount
                return {"sold": target, "amount": amount}
            return {"error": "Insufficient holdings"}
        
        elif action == "transfer":
            return {"transferred": amount, "to": target}
        
        return {"error": "Unknown action"}


# Create bot with fence
config = FenceConfig(
    agent_id="trading-bot-002",
    spending_limit=1000.0,
    blocked_actions=["withdraw_all"],  # Never allow this
    blocked_targets=["suspicious-wallet"],  # Block known bad actors
    risk_threshold=RiskLevel.HIGH,
    auto_kill_on_critical=True
)

fence = RuntimeFence(config)
bot = TradingBot(fence)

# Bot actions go through fence
print("\n--- Trading Bot Actions ---")
print(bot.execute("buy", "BTC", 100.0))
print(bot.execute("buy", "ETH", 50.0))
print(bot.execute("sell", "BTC", 30.0))

# This would be blocked
try:
    bot.execute("transfer", "suspicious-wallet", 500.0)
except PermissionError as e:
    print(f"Blocked: {e}")

# Check fence status
print("\n--- Fence Status ---")
print(bot.fence.get_status())


# ======================
# EXAMPLE 3: Manual kill switch
# ======================

print("\n--- Kill Switch Demo ---")

# Something goes wrong - kill the agent
bot.fence.kill("Detected anomalous behavior")

# Now all actions are blocked
try:
    bot.execute("buy", "DOGE", 10.0)
except PermissionError as e:
    print(f"After kill: {e}")

# Check status
print(f"Agent killed: {bot.fence.killed}")


# ======================
# Usage with any AI framework
# ======================
"""
# With LangChain
from langchain.agents import AgentExecutor

fence = create_fence("langchain-agent")

@fence.wrap_function("tool_call", "external")
def run_tool(tool_name, input):
    return agent.run(tool_name, input)


# With AutoGPT-style agents
fence = create_fence("autogpt-agent", spending_limit=100)

class SafeAutoGPT(FencedAgent):
    def _do_action(self, action, target, amount, **kwargs):
        # Your AutoGPT logic here
        pass
"""

if __name__ == "__main__":
    from runtime_fence import RuntimeFence
    
    print("\n=== Runtime Fence Example Complete ===")
    print("The fence validates every action before it happens.")
    print("If risk is too high, the action is blocked.")
    print("Critical risk = automatic kill switch.")
