# Integration Guide

Step-by-step guides for integrating $KILLSWITCH with popular AI frameworks.

---

## Table of Contents

1. [LangChain](#langchain)
2. [AutoGPT](#autogpt)
3. [OpenAI API](#openai-api)
4. [Anthropic Claude](#anthropic-claude)
5. [CrewAI](#crewai)
6. [Custom Agents](#custom-agents)

---

## LangChain

### Installation

```bash
pip install runtime-fence langchain openai
```

### Basic Integration

```python
from langchain.llms import OpenAI
from langchain.agents import initialize_agent, Tool
from runtime_fence import RuntimeFence, FenceConfig

# Initialize fence
fence = RuntimeFence(FenceConfig(
    agent_id="langchain-agent",
    blocked_actions=["delete", "exec"],
    spending_limit=100.0
))

# Wrap your functions
@fence.wrap_function("web_search", "external_api")
def web_search(query: str) -> str:
    # Your search implementation
    return f"Results for: {query}"

@fence.wrap_function("file_read", "local_filesystem")
def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()

# Create agent with protected tools
tools = [
    Tool(name="Search", func=web_search, description="Search the web"),
    Tool(name="ReadFile", func=read_file, description="Read a file"),
]

agent = initialize_agent(tools, OpenAI(), agent_type="zero-shot-react-description")

# Run with fence protection
result = agent.run("Find information about AI safety")
print(result)
```
```

### LangChain Callback Handler

For automatic monitoring of all LangChain operations, see the [langchain_integration.py](https://github.com/RunTimeAdmin/ai-agent-killswitch/blob/main/packages/python/langchain_integration.py) example that includes:

- `FenceCallbackHandler` - Monitors all tool calls
- `wrap_tools()` - Automatically wraps tool lists
- `create_fenced_agent()` - Creates pre-configured safe agents
- Preset configurations for coding, data analysis, and web automation

Example:

```python
from langchain_integration import create_fenced_agent, Preset

# Create a coding assistant with safety guardrails
agent = create_fenced_agent(
    preset=Preset.CODING_ASSISTANT,
    agent_id="my-coder"
)

# All operations automatically monitored
result = agent.run("Write a Python script")
```

---

## AutoGPT

### Wrapper Script

Create `run_autogpt_protected.py`:

```python
import os
import sys
from runtime_fence import RuntimeFence, FenceConfig

# Initialize fence before AutoGPT starts
fence = RuntimeFence(FenceConfig(
    agent_id=os.getenv("KILLSWITCH_AGENT_ID", "autogpt"),
    offline_mode=True,
    blocked_actions=[
        "spawn_agent",
        "modify_self",
        "execute_code",
        "delete",
        "rm",
        "sudo",
        "wget",
        "curl"
    ],
    blocked_targets=[
        ".env",
        "*.key",
        "*.pem",
        "/etc/*",
        "~/.ssh/*"
    ]
))

# Monkey-patch dangerous functions
import subprocess
original_run = subprocess.run

@fence.wrap_function("shell_exec", "subprocess")
def protected_run(*args, **kwargs):
    return original_run(*args, **kwargs)

subprocess.run = protected_run

# Now import and run AutoGPT
from autogpt.main import main
main()
```

### Run Protected

```bash
python run_autogpt_protected.py
```

---

## OpenAI API

### Direct API Wrapping

```python
import openai
from runtime_fence import RuntimeFence, FenceConfig

fence = RuntimeFence(FenceConfig(
    agent_id="openai-agent",
    blocked_actions=["delete", "exec"],
    spending_limit=100.0
))

# Wrap the OpenAI client
@fence.wrap_function("llm_call", "openai_api")
def chat_completion(messages: list, model: str = "gpt-4"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages
    )
    return response.choices[0].message.content

# Usage
result = chat_completion([
    {"role": "user", "content": "Explain quantum computing"}
])
```

### Function Calling Protection

```python
from runtime_fence import RuntimeFence, FenceConfig

fence = RuntimeFence(FenceConfig(
    agent_id="openai-functions",
    blocked_actions=["delete_file", "execute_code"]
))

def execute_function_call(function_name: str, arguments: dict):
    # Validate function is allowed
    result = fence.validate(
        action=function_name,
        target=str(arguments)
    )
    
    if not result.allowed:
        return {"error": f"Blocked: {result.reasons}"}
    
    # Execute the function
    if function_name == "get_weather":
        return get_weather(**arguments)
    elif function_name == "search_web":
        return search_web(**arguments)

# Use with OpenAI function calling
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=messages,
    functions=functions
)

if response.choices[0].message.get("function_call"):
    fc = response.choices[0].message.function_call
    result = execute_function_call(fc.name, json.loads(fc.arguments))
```

---

## Anthropic Claude

### Basic Integration

```python
import anthropic
from runtime_fence import RuntimeFence, FenceConfig

fence = RuntimeFence(FenceConfig(
    agent_id="claude-agent",
    blocked_actions=["delete", "exec"],
    spending_limit=100.0
))

client = anthropic.Anthropic()

@fence.wrap_function("llm_call", "anthropic_api")
def ask_claude(prompt: str, max_tokens: int = 1024):
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

# Usage
response = ask_claude("Explain quantum computing")
```

### Tool Use with Claude

```python
from runtime_fence import RuntimeFence, FenceConfig

fence = RuntimeFence(FenceConfig(
    agent_id="claude-tools",
    blocked_actions=["delete", "rm", "sudo"]
))

@fence.wrap_function("tool_use", "claude_tools")
def execute_claude_tool(tool_name: str, tool_input: dict):
    """Execute a tool requested by Claude"""
    
    # Fence validates the tool call
    result = fence.validate(
        action=f"tool:{tool_name}",
        target=str(tool_input)
    )
    
    if not result.allowed:
        return {"error": f"Tool blocked: {result.reasons}"}
    
    # Execute tool
    if tool_name == "computer":
        return execute_computer_action(tool_input)
    elif tool_name == "bash":
        return execute_bash(tool_input)

# Claude tool use loop with protection
while True:
    response = client.messages.create(
        model="claude-3-opus-20240229",
        messages=messages,
        tools=tools
    )
    
    if response.stop_reason == "tool_use":
        for block in response.content:
            if block.type == "tool_use":
                result = execute_claude_tool(block.name, block.input)
                # Continue conversation with result
    else:
        break
```

---

## CrewAI

### Agent Protection

```python
from crewai import Agent, Task, Crew
from runtime_fence import RuntimeFence, FenceConfig

# Initialize fence
fence = RuntimeFence(FenceConfig(
    agent_id="crewai-crew",
    blocked_actions=["delete", "exec"],
    spending_limit=100.0
))

# Define agents with wrapped functions
class ResearchAgent:
    @fence.wrap_function("web_search", "research")
    def search(self, query: str):
        # Your search implementation
        return f"Results for: {query}"

class WriterAgent:
    @fence.wrap_function("write_content", "writing")
    def write(self, content: str):
        # Your writing implementation
        return f"Written: {content}"

# Create crew
researcher = ResearchAgent()
writer = WriterAgent()

# Run with protection
research_results = researcher.search("AI safety best practices")
article = writer.write(research_results)
```

---

## Custom Agents

### Decorator Pattern

```python
from runtime_fence import RuntimeFence, FenceConfig

fence = RuntimeFence(FenceConfig(
    agent_id="custom-agent",
    blocked_actions=["delete", "rm", "sudo"],
    spending_limit=100.0
))

class MyAgent:
    @fence.wrap_function("file_read", "filesystem")
    def read_file(self, path: str) -> str:
        with open(path, 'r') as f:
            return f.read()
    
    @fence.wrap_function("file_write", "filesystem")
    def write_file(self, path: str, content: str):
        with open(path, 'w') as f:
            f.write(content)
    
    @fence.wrap_function("api_call", "external")
    def call_api(self, url: str, data: dict):
        return requests.post(url, json=data)
    
    @fence.wrap_function("shell_exec", "dangerous")
    def run_command(self, cmd: str):
        return subprocess.run(cmd, shell=True, capture_output=True)

# Usage
agent = MyAgent()
content = agent.read_file("document.txt")  # Allowed
agent.write_file("output.txt", content)    # Allowed
agent.run_command("rm -rf /")              # BLOCKED by fence
```

---

## Environment Variables

Runtime Fence supports offline mode by default (no API calls):

```bash
# Optional configuration
FENCE_AGENT_ID=my-agent
FENCE_LOG_LEVEL=INFO
```

For full configuration options, see [Configuration Guide](../wiki/Configuration.md).

---

## Testing Your Integration

```python
from runtime_fence import RuntimeFence, FenceConfig

# Create fence with test config
fence = RuntimeFence(FenceConfig(
    agent_id="test-agent",
    offline_mode=True,
    blocked_actions=["delete"]
))

# Test validation
result = fence.validate("read", "file.txt")
assert result.allowed == True

result = fence.validate("delete", "file.txt")
assert result.allowed == False
assert "delete" in result.reasons[0].lower()

print("Integration tests passed!")
```

---

## Related Documentation

- [API Reference](API-Reference.md)
- [Troubleshooting & FAQ](Troubleshooting-FAQ.md)
- [Security Hardening](Security-Hardening.md)
