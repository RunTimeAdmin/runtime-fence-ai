"""
Runtime Fence Agent Scanner
Auto-detects AI agents running on your machine.
"""

import os
import sys
import time
import psutil
import json
from typing import Dict, List, Set
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("agent_scanner")


@dataclass
class DetectedAgent:
    """Represents a detected AI agent."""
    name: str
    pid: int
    process_name: str
    command_line: str
    confidence: float  # 0-1 how confident we are this is an AI agent
    risk_level: str    # low, medium, high


# Signatures for known AI agents
AGENT_SIGNATURES = {
    # Process name patterns -> Agent info
    "autogpt": {
        "patterns": ["autogpt", "auto-gpt", "auto_gpt"],
        "risk": "high",
        "description": "AutoGPT autonomous agent"
    },
    "babyagi": {
        "patterns": ["babyagi", "baby-agi", "baby_agi"],
        "risk": "high",
        "description": "BabyAGI task agent"
    },
    "langchain": {
        "patterns": ["langchain", "langserve"],
        "risk": "medium",
        "description": "LangChain agent framework"
    },
    "crewai": {
        "patterns": ["crewai", "crew-ai", "crew_ai"],
        "risk": "high",
        "description": "CrewAI multi-agent system"
    },
    "cursor": {
        "patterns": ["cursor.exe", "Cursor.exe", "cursor-helper"],
        "risk": "medium",
        "description": "Cursor AI code editor"
    },
    "copilot": {
        "patterns": ["copilot", "gh-copilot"],
        "risk": "low",
        "description": "GitHub Copilot"
    },
    "aider": {
        "patterns": ["aider"],
        "risk": "medium",
        "description": "Aider AI coding assistant"
    },
    "gpt_engineer": {
        "patterns": ["gpt-engineer", "gpt_engineer", "gptengineer"],
        "risk": "high",
        "description": "GPT Engineer code generator"
    },
    "devin": {
        "patterns": ["devin", "cognition"],
        "risk": "high",
        "description": "Devin AI developer"
    },
    "openinterpreter": {
        "patterns": ["interpreter", "open-interpreter"],
        "risk": "high",
        "description": "Open Interpreter - executes code"
    },
    "smol_developer": {
        "patterns": ["smol", "smol-developer"],
        "risk": "medium",
        "description": "Smol Developer"
    },
    "superagi": {
        "patterns": ["superagi", "super-agi"],
        "risk": "high",
        "description": "SuperAGI autonomous agent"
    },
    "agentgpt": {
        "patterns": ["agentgpt", "agent-gpt"],
        "risk": "high",
        "description": "AgentGPT web agent"
    },
    "chatdev": {
        "patterns": ["chatdev", "chat-dev"],
        "risk": "medium",
        "description": "ChatDev software development"
    },
    "metagpt": {
        "patterns": ["metagpt", "meta-gpt"],
        "risk": "high",
        "description": "MetaGPT multi-agent"
    }
}

# API endpoints to monitor (indicates AI agent activity)
AI_API_INDICATORS = [
    "api.openai.com",
    "api.anthropic.com",
    "api.cohere.ai",
    "api.mistral.ai",
    "generativelanguage.googleapis.com",  # Google AI
    "api.together.xyz",
    "api.groq.com",
    "api.perplexity.ai",
    "api.replicate.com"
]


class AgentScanner:
    """Scans system for running AI agents."""
    
    def __init__(self):
        self.detected_agents: Dict[int, DetectedAgent] = {}
        self.monitoring = False
        self.scan_interval = 5  # seconds
        
    def scan_once(self) -> List[DetectedAgent]:
        """Perform a single scan of running processes."""
        detected = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                info = proc.info
                pid = info['pid']
                name = info['name'] or ""
                cmdline = " ".join(info['cmdline'] or [])
                
                # Check against known signatures
                for agent_name, config in AGENT_SIGNATURES.items():
                    for pattern in config['patterns']:
                        if pattern.lower() in name.lower() or pattern.lower() in cmdline.lower():
                            agent = DetectedAgent(
                                name=agent_name,
                                pid=pid,
                                process_name=name,
                                command_line=cmdline[:200],  # Truncate
                                confidence=0.9 if pattern in name else 0.7,
                                risk_level=config['risk']
                            )
                            detected.append(agent)
                            self.detected_agents[pid] = agent
                            break
                
                # Also check for Python/Node processes calling AI APIs
                if name.lower() in ['python', 'python.exe', 'node', 'node.exe']:
                    for api in AI_API_INDICATORS:
                        if api in cmdline:
                            agent = DetectedAgent(
                                name=f"unknown_agent ({api.split('.')[1]})",
                                pid=pid,
                                process_name=name,
                                command_line=cmdline[:200],
                                confidence=0.6,
                                risk_level="medium"
                            )
                            detected.append(agent)
                            self.detected_agents[pid] = agent
                            break
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return detected
    
    def start_monitoring(self, callback=None):
        """Start continuous monitoring."""
        self.monitoring = True
        logger.info("Agent monitoring started")
        
        while self.monitoring:
            newly_detected = self.scan_once()
            
            if newly_detected and callback:
                for agent in newly_detected:
                    callback(agent)
            
            # Clean up dead processes
            for pid in list(self.detected_agents.keys()):
                if not psutil.pid_exists(pid):
                    del self.detected_agents[pid]
            
            time.sleep(self.scan_interval)
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False
        logger.info("Agent monitoring stopped")
    
    def get_summary(self) -> Dict:
        """Get summary of detected agents."""
        high_risk = [a for a in self.detected_agents.values() if a.risk_level == "high"]
        medium_risk = [a for a in self.detected_agents.values() if a.risk_level == "medium"]
        low_risk = [a for a in self.detected_agents.values() if a.risk_level == "low"]
        
        return {
            "total_agents": len(self.detected_agents),
            "high_risk": len(high_risk),
            "medium_risk": len(medium_risk),
            "low_risk": len(low_risk),
            "agents": [
                {
                    "name": a.name,
                    "pid": a.pid,
                    "risk": a.risk_level,
                    "confidence": a.confidence
                }
                for a in self.detected_agents.values()
            ]
        }


def on_agent_detected(agent: DetectedAgent):
    """Callback when an agent is detected."""
    emoji = "🔴" if agent.risk_level == "high" else "🟡" if agent.risk_level == "medium" else "🟢"
    logger.info(f"{emoji} DETECTED: {agent.name} (PID: {agent.pid}, Risk: {agent.risk_level})")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           RUNTIME FENCE - AGENT SCANNER                      ║
    ║                                                              ║
    ║  Automatically detects AI agents running on your system.    ║
    ║  Monitors for: AutoGPT, LangChain, CrewAI, Cursor, etc.    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    scanner = AgentScanner()
    
    if "--once" in sys.argv:
        # Single scan
        agents = scanner.scan_once()
        if agents:
            print(f"\nFound {len(agents)} agent(s):")
            for a in agents:
                print(f"  - {a.name} (PID: {a.pid}, Risk: {a.risk_level})")
        else:
            print("\nNo AI agents detected.")
    else:
        # Continuous monitoring
        print("\nMonitoring for AI agents... (Ctrl+C to stop)\n")
        try:
            scanner.start_monitoring(callback=on_agent_detected)
        except KeyboardInterrupt:
            scanner.stop_monitoring()
            print("\n" + json.dumps(scanner.get_summary(), indent=2))
