# Quick Start

Get $KILLSWITCH running in under 5 minutes.

## 1. Install

```bash
pip install runtime-fence
```

## 2. Create a Fence

```python
from runtime_fence import RuntimeFence, FenceConfig

config = FenceConfig(
    agent_id="my-first-agent",
    blocked_actions=["delete", "exec"],
    blocked_targets=["production", ".env"],
    spending_limit=50.0
)

fence = RuntimeFence(config)
```

## 3. Validate Actions

```python
# Check if an action is allowed
result = fence.validate("read", "document.txt")

if result.allowed:
    print("Action allowed!")
else:
    print(f"Blocked: {result.reasons}")
```

## 4. Wrap Existing Functions

```python
@fence.wrap_function("api_call", "external")
def my_api_call():
    # Your existing code
    return requests.get("https://api.example.com")

# Now it goes through the fence
my_api_call()
```

## 5. Try the Kill Switch

```python
# Activate kill switch
fence.kill("Testing kill switch")

# All actions are now blocked
result = fence.validate("read", "anything")
print(result.allowed)  # False
print(result.reasons)  # ['Kill switch is active: Testing kill switch']

# Resume
fence.resume()
```

## 6. Run a Quick Test

```bash
fence test
```

Expected output:
```
Testing Runtime Fence...

  [PASS] read -> file.txt: allowed
  [PASS] delete -> data: blocked
  [PASS] exec -> command: blocked
  [PASS] write -> production: blocked
  [PASS] read -> .env: blocked

Tests: 5/5 passed
```

## Next Steps

- [Configuration](Configuration) - Customize your fence
- [Agent Presets](Agent-Presets) - Pre-built configurations
- [API Reference](API-Reference) - REST API documentation
