"""
LangChain Integration for $KILLSWITCH Runtime Fence

This module provides seamless integration between LangChain agents and Runtime Fence,
allowing you to add safety controls to any LangChain application.

Installation:
    pip install runtime-fence langchain

Basic Usage:
    from runtime_fence import RuntimeFence, FenceConfig
    from langchain_integration import FencedLangChainAgent
    
    fence = RuntimeFence(FenceConfig(agent_id="my-agent"))
    agent = FencedLangChainAgent(fence=fence, llm=your_llm, tools=your_tools)
"""

from typing import Any, Dict, List, Optional, Union
from runtime_fence import RuntimeFence, FenceConfig, RiskLevel
import logging

logger = logging.getLogger(__name__)

try:
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.tools import BaseTool, Tool
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain_core.language_models import BaseLanguageModel
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not installed. Install with: pip install langchain")


class FenceCallbackHandler(BaseCallbackHandler):
    """LangChain callback that validates actions through Runtime Fence."""
    
    def __init__(self, fence: RuntimeFence):
        self.fence = fence
        self.current_tool = None
        
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        """Called when a tool is about to execute."""
        tool_name = serialized.get("name", "unknown_tool")
        
        # Validate through fence
        result = self.fence.validate(
            action=tool_name,
            target=input_str[:100],  # First 100 chars as target identifier
            context={"full_input": input_str}
        )
        
        if not result.allowed:
            error_msg = f"Runtime Fence blocked tool '{tool_name}': {', '.join(result.reasons)}"
            logger.warning(error_msg)
            raise PermissionError(error_msg)
        
        if result.risk_level == RiskLevel.HIGH:
            logger.warning(f"High-risk tool execution: {tool_name} (score: {result.risk_score})")
        
        self.current_tool = tool_name
        
    def on_tool_end(self, output: str, **kwargs):
        """Called when a tool finishes executing."""
        logger.info(f"Tool '{self.current_tool}' completed successfully")
        self.current_tool = None
        
    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs):
        """Called when a tool encounters an error."""
        logger.error(f"Tool '{self.current_tool}' failed: {error}")
        self.current_tool = None


class FencedTool(BaseTool):
    """Wrapper for LangChain tools that adds Runtime Fence validation."""
    
    name: str
    description: str
    func: callable
    fence: RuntimeFence
    
    def _run(self, query: str) -> str:
        """Execute the tool through the fence."""
        # Validate action
        result = self.fence.validate(
            action=self.name,
            target=query[:100],
            context={"query": query}
        )
        
        if not result.allowed:
            return f"[BLOCKED by Runtime Fence] {', '.join(result.reasons)}"
        
        # Execute original function
        try:
            return self.func(query)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Async version."""
        # For now, just call the sync version
        return self._run(query)


def wrap_tools_with_fence(tools: List[BaseTool], fence: RuntimeFence) -> List[FencedTool]:
    """
    Wrap a list of LangChain tools with Runtime Fence protection.
    
    Args:
        tools: List of LangChain tools to wrap
        fence: Runtime Fence instance
        
    Returns:
        List of fenced tools
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain not installed. Install with: pip install langchain")
    
    fenced_tools = []
    for tool in tools:
        fenced_tool = FencedTool(
            name=tool.name,
            description=tool.description,
            func=tool.func if hasattr(tool, 'func') else tool._run,
            fence=fence
        )
        fenced_tools.append(fenced_tool)
    
    return fenced_tools


class FencedLangChainAgent:
    """
    LangChain agent with integrated Runtime Fence protection.
    
    All tool executions are validated through the fence before execution.
    """
    
    def __init__(
        self,
        fence: RuntimeFence,
        llm: 'BaseLanguageModel',
        tools: List[BaseTool],
        agent_kwargs: Optional[Dict] = None,
        executor_kwargs: Optional[Dict] = None
    ):
        """
        Initialize fenced LangChain agent.
        
        Args:
            fence: Runtime Fence instance
            llm: Language model to use
            tools: List of tools (will be automatically wrapped)
            agent_kwargs: Arguments for agent creation
            executor_kwargs: Arguments for agent executor
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not installed. Install with: pip install langchain")
        
        self.fence = fence
        self.llm = llm
        
        # Wrap tools with fence
        self.fenced_tools = wrap_tools_with_fence(tools, fence)
        
        # Create callback handler
        self.fence_callback = FenceCallbackHandler(fence)
        
        # Create agent
        agent_kwargs = agent_kwargs or {}
        executor_kwargs = executor_kwargs or {}
        
        # Add fence callback to executor
        callbacks = executor_kwargs.get('callbacks', [])
        callbacks.append(self.fence_callback)
        executor_kwargs['callbacks'] = callbacks
        
        # Create React agent
        from langchain import hub
        prompt = hub.pull("hwchase17/react")
        
        agent = create_react_agent(llm, self.fenced_tools, prompt)
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.fenced_tools,
            **executor_kwargs
        )
    
    def run(self, query: str) -> str:
        """Run the agent with fence protection."""
        try:
            return self.executor.invoke({"input": query})
        except PermissionError as e:
            logger.error(f"Agent blocked by fence: {e}")
            return f"Action blocked: {e}"
    
    def kill(self, reason: str = "Manual kill"):
        """Activate kill switch."""
        self.fence.kill(reason)


# Quick setup functions for common use cases

def create_safe_coding_agent(llm: 'BaseLanguageModel', tools: List[BaseTool]) -> FencedLangChainAgent:
    """
    Create a coding agent with safe defaults.
    
    Blocks: exec, shell, rm, sudo, delete operations
    """
    fence = RuntimeFence(FenceConfig(
        agent_id="coding-assistant",
        blocked_actions=["exec", "shell", "rm", "sudo", "delete", "drop_table"],
        blocked_targets=["production", ".env", "api_keys", "/etc/", "C:\\Windows"],
        spending_limit=10.0,
        risk_threshold=RiskLevel.MEDIUM
    ))
    
    return FencedLangChainAgent(fence=fence, llm=llm, tools=tools)


def create_safe_data_agent(llm: 'BaseLanguageModel', tools: List[BaseTool]) -> FencedLangChainAgent:
    """
    Create a data analysis agent with safe defaults.
    
    Blocks: delete, drop, truncate operations
    Protects: PII, sensitive data
    """
    fence = RuntimeFence(FenceConfig(
        agent_id="data-analyst",
        blocked_actions=["delete", "drop_table", "truncate", "drop_database"],
        blocked_targets=["pii", "ssn", "credit_card", "password"],
        spending_limit=50.0,
        risk_threshold=RiskLevel.MEDIUM
    ))
    
    return FencedLangChainAgent(fence=fence, llm=llm, tools=tools)


def create_safe_web_agent(llm: 'BaseLanguageModel', tools: List[BaseTool]) -> FencedLangChainAgent:
    """
    Create a web automation agent with safe defaults.
    
    Blocks: login, purchase, payment actions
    """
    fence = RuntimeFence(FenceConfig(
        agent_id="web-automator",
        blocked_actions=["login", "purchase", "checkout", "submit_payment"],
        blocked_targets=["credit_card", "payment", "checkout"],
        spending_limit=0.0,  # No spending allowed
        risk_threshold=RiskLevel.MEDIUM
    ))
    
    return FencedLangChainAgent(fence=fence, llm=llm, tools=tools)


# Example usage
if __name__ == "__main__":
    print("LangChain + Runtime Fence Integration Example")
    print("=" * 50)
    
    if not LANGCHAIN_AVAILABLE:
        print("ERROR: LangChain not installed!")
        print("Install with: pip install langchain langchain-openai")
        exit(1)
    
    # Example: Create a safe coding agent
    print("\nExample: Safe Coding Agent")
    print("-" * 50)
    
    # Note: This is a template - you need to provide your own LLM and tools
    print("""
    from langchain_openai import ChatOpenAI
    from langchain.tools import Tool
    
    # Create LLM
    llm = ChatOpenAI(temperature=0)
    
    # Create tools
    tools = [
        Tool(
            name="python_repl",
            description="Execute Python code",
            func=lambda x: exec(x)
        ),
        Tool(
            name="file_read",
            description="Read a file",
            func=lambda x: open(x).read()
        )
    ]
    
    # Create safe agent
    agent = create_safe_coding_agent(llm=llm, tools=tools)
    
    # Run query
    result = agent.run("Read the config file and execute the setup script")
    print(result)
    
    # If agent misbehaves
    agent.kill("Suspicious behavior detected")
    """)
    
    print("\nFor full working examples, see:")
    print("https://github.com/RunTimeAdmin/ai-agent-killswitch/tree/main/examples")
