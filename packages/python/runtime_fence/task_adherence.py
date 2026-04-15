"""
Task Adherence Monitor - Detecting Agentic Drift

This module monitors whether an AI agent stays on-task or drifts
from its original assignment. An agent might perform only "allowed"
actions but drift toward unintended goals.

Example drift scenarios:
- Email agent: allowed to send emails, but starts emailing competitors
- Data agent: allowed to query DB, but starts querying unrelated tables
- Code agent: allowed to write code, but starts modifying system files

The monitor compares current actions against the original task embedding
using cosine similarity and tracks cumulative drift over time.

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import math
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import json

logger = logging.getLogger(__name__)


# =============================================================================
# DRIFT SEVERITY
# =============================================================================

class DriftSeverity(Enum):
    """Severity levels for task drift"""
    NONE = "none"           # On task
    MINOR = "minor"         # Slight deviation, acceptable
    MODERATE = "moderate"   # Noticeable drift, warning
    MAJOR = "major"         # Significant drift, intervention needed
    CRITICAL = "critical"   # Complete task abandonment, kill agent


# Thresholds for drift severity (cosine similarity)
DRIFT_THRESHOLDS = {
    DriftSeverity.NONE: 0.85,      # >= 85% similarity = on task
    DriftSeverity.MINOR: 0.70,     # 70-85% = minor drift
    DriftSeverity.MODERATE: 0.50,  # 50-70% = moderate drift
    DriftSeverity.MAJOR: 0.30,     # 30-50% = major drift
    DriftSeverity.CRITICAL: 0.0,   # < 30% = critical drift
}


@dataclass
class DriftReport:
    """Report on agent's task adherence"""
    agent_id: str
    original_task: str
    current_similarity: float      # 0-1, higher = more on-task
    drift_severity: DriftSeverity
    drift_trend: str               # "stable", "drifting", "recovering"
    actions_analyzed: int
    flagged_actions: List[str]
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "original_task": self.original_task[:100],
            "current_similarity": round(self.current_similarity, 3),
            "drift_severity": self.drift_severity.value,
            "drift_trend": self.drift_trend,
            "actions_analyzed": self.actions_analyzed,
            "flagged_actions": self.flagged_actions[:5],
            "recommendation": self.recommendation,
            "timestamp": self.timestamp.isoformat()
        }
    
    @property
    def needs_intervention(self) -> bool:
        return self.drift_severity in [
            DriftSeverity.MAJOR,
            DriftSeverity.CRITICAL
        ]


# =============================================================================
# SIMPLE EMBEDDING (No External Dependencies)
# =============================================================================

class SimpleEmbedding:
    """
    Simple TF-IDF-like embedding for text similarity.
    
    For production, replace with sentence-transformers or OpenAI embeddings.
    This provides baseline functionality without external dependencies.
    """
    
    def __init__(self):
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._doc_count = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        import re
        text = text.lower()
        tokens = re.findall(r'\b[a-z][a-z0-9_]*\b', text)
        return [t for t in tokens if len(t) > 2]
    
    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency"""
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        # Normalize
        total = sum(tf.values())
        if total > 0:
            tf = {k: v / total for k, v in tf.items()}
        return tf
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Returns a sparse vector as a list of floats.
        """
        tokens = self._tokenize(text)
        tf = self._compute_tf(tokens)
        
        # Build vocabulary on the fly
        for token in tokens:
            if token not in self._vocab:
                self._vocab[token] = len(self._vocab)
        
        # Create vector
        vector = [0.0] * max(len(self._vocab), 1)
        for token, freq in tf.items():
            if token in self._vocab:
                vector[self._vocab[token]] = freq
        
        # Normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        # Pad shorter vector
        max_len = max(len(vec1), len(vec2))
        v1 = vec1 + [0.0] * (max_len - len(vec1))
        v2 = vec2 + [0.0] * (max_len - len(vec2))
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


# =============================================================================
# ACTION CLASSIFIER
# =============================================================================

class ActionClassifier:
    """
    Classifies actions into semantic categories for drift detection.
    """
    
    # Action category keywords
    CATEGORIES = {
        "file_operation": [
            "read", "write", "open", "close", "delete", "create",
            "file", "path", "directory", "folder"
        ],
        "network_operation": [
            "request", "http", "api", "url", "fetch", "download",
            "upload", "socket", "connect"
        ],
        "data_operation": [
            "query", "select", "insert", "update", "database", "sql",
            "table", "record", "data"
        ],
        "email_operation": [
            "email", "mail", "send", "recipient", "subject", "smtp",
            "inbox", "message"
        ],
        "code_operation": [
            "code", "function", "class", "module", "import", "compile",
            "execute", "script"
        ],
        "system_operation": [
            "system", "process", "shell", "command", "sudo", "admin",
            "config", "setting"
        ],
    }
    
    def classify(self, action_description: str) -> Tuple[str, float]:
        """
        Classify an action into a category.
        
        Returns (category, confidence)
        """
        action_lower = action_description.lower()
        
        scores = {}
        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in action_lower)
            if score > 0:
                scores[category] = score / len(keywords)
        
        if not scores:
            return "unknown", 0.0
        
        best_category = max(scores, key=scores.get)
        return best_category, scores[best_category]


# =============================================================================
# TASK ADHERENCE MONITOR
# =============================================================================

class TaskAdherenceMonitor:
    """
    Monitors whether an AI agent stays on-task or drifts.
    
    The monitor:
    1. Takes the original task description as a baseline
    2. Tracks all agent actions
    3. Computes similarity between actions and original task
    4. Detects drift patterns over time
    5. Triggers alerts when drift exceeds thresholds
    
    Usage:
        monitor = TaskAdherenceMonitor(
            agent_id="agent-123",
            original_task="Send weekly reports to team members"
        )
        
        # Record actions
        monitor.record_action("Querying employee email addresses")
        monitor.record_action("Composing report email")
        monitor.record_action("Sending email to john@company.com")
        
        # Check drift
        report = monitor.check_drift()
        if report.needs_intervention:
            kill_agent(agent_id)
    """
    
    def __init__(
        self,
        agent_id: str,
        original_task: str,
        window_size: int = 20,
        on_drift: Callable[[DriftReport], None] = None
    ):
        """
        Initialize task adherence monitor.
        
        Args:
            agent_id: Unique identifier for the agent
            original_task: The original task description
            window_size: Number of recent actions to analyze
            on_drift: Callback when significant drift detected
        """
        self.agent_id = agent_id
        self.original_task = original_task
        self.window_size = window_size
        self.on_drift = on_drift
        
        # Initialize embedding
        self.embedder = SimpleEmbedding()
        self.classifier = ActionClassifier()
        
        # Compute task embedding
        self.task_embedding = self.embedder.embed(original_task)
        self.task_category, _ = self.classifier.classify(original_task)
        
        # Action history (sliding window)
        self.action_history: deque = deque(maxlen=window_size)
        self.similarity_history: deque = deque(maxlen=window_size)
        
        # Drift tracking
        self.total_actions = 0
        self.flagged_actions: List[Tuple[str, float]] = []
        self.last_report: Optional[DriftReport] = None
        
        logger.info(
            f"TaskAdherenceMonitor initialized for agent {agent_id}\n"
            f"  Task: {original_task[:50]}...\n"
            f"  Category: {self.task_category}"
        )
    
    def record_action(
        self,
        action_description: str,
        metadata: Dict[str, Any] = None
    ) -> float:
        """
        Record an agent action and compute similarity to task.
        
        Args:
            action_description: Description of the action taken
            metadata: Optional metadata about the action
            
        Returns:
            Similarity score (0-1)
        """
        self.total_actions += 1
        
        # Compute action embedding
        action_embedding = self.embedder.embed(action_description)
        
        # Compute similarity to original task
        similarity = SimpleEmbedding.cosine_similarity(
            self.task_embedding,
            action_embedding
        )
        
        # Classify action
        action_category, _ = self.classifier.classify(action_description)
        
        # Store in history
        action_record = {
            "description": action_description,
            "similarity": similarity,
            "category": action_category,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.action_history.append(action_record)
        self.similarity_history.append(similarity)
        
        # Flag low-similarity actions
        severity = self._get_severity(similarity)
        if severity in [DriftSeverity.MAJOR, DriftSeverity.CRITICAL]:
            self.flagged_actions.append((action_description, similarity))
            logger.warning(
                f"Low-similarity action detected:\n"
                f"  Action: {action_description[:50]}\n"
                f"  Similarity: {similarity:.2f}\n"
                f"  Severity: {severity.value}"
            )
        
        return similarity
    
    def check_drift(self) -> DriftReport:
        """
        Analyze current drift status.
        
        Returns:
            DriftReport with analysis results
        """
        if not self.similarity_history:
            return DriftReport(
                agent_id=self.agent_id,
                original_task=self.original_task,
                current_similarity=1.0,
                drift_severity=DriftSeverity.NONE,
                drift_trend="stable",
                actions_analyzed=0,
                flagged_actions=[],
                recommendation="No actions recorded yet"
            )
        
        # Current similarity (average of recent actions)
        current_sim = sum(self.similarity_history) / len(self.similarity_history)
        
        # Determine severity
        severity = self._get_severity(current_sim)
        
        # Analyze trend
        trend = self._analyze_trend()
        
        # Generate recommendation
        recommendation = self._get_recommendation(severity, trend)
        
        # Get flagged action descriptions
        flagged = [desc for desc, _ in self.flagged_actions[-5:]]
        
        report = DriftReport(
            agent_id=self.agent_id,
            original_task=self.original_task,
            current_similarity=current_sim,
            drift_severity=severity,
            drift_trend=trend,
            actions_analyzed=self.total_actions,
            flagged_actions=flagged,
            recommendation=recommendation
        )
        
        self.last_report = report
        
        # Trigger callback if needed
        if report.needs_intervention and self.on_drift:
            self.on_drift(report)
        
        return report
    
    def _get_severity(self, similarity: float) -> DriftSeverity:
        """Determine drift severity from similarity score"""
        if similarity >= DRIFT_THRESHOLDS[DriftSeverity.NONE]:
            return DriftSeverity.NONE
        elif similarity >= DRIFT_THRESHOLDS[DriftSeverity.MINOR]:
            return DriftSeverity.MINOR
        elif similarity >= DRIFT_THRESHOLDS[DriftSeverity.MODERATE]:
            return DriftSeverity.MODERATE
        elif similarity >= DRIFT_THRESHOLDS[DriftSeverity.MAJOR]:
            return DriftSeverity.MAJOR
        else:
            return DriftSeverity.CRITICAL
    
    def _analyze_trend(self) -> str:
        """Analyze whether drift is increasing, decreasing, or stable"""
        if len(self.similarity_history) < 5:
            return "stable"
        
        # Compare first half to second half
        mid = len(self.similarity_history) // 2
        first_half = list(self.similarity_history)[:mid]
        second_half = list(self.similarity_history)[mid:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        diff = avg_second - avg_first
        
        if diff < -0.1:
            return "drifting"  # Getting worse
        elif diff > 0.1:
            return "recovering"  # Getting better
        else:
            return "stable"
    
    def _get_recommendation(
        self,
        severity: DriftSeverity,
        trend: str
    ) -> str:
        """Generate recommendation based on drift analysis"""
        recommendations = {
            (DriftSeverity.NONE, "stable"): "Agent on task. No action needed.",
            (DriftSeverity.NONE, "drifting"): "Watch closely - early drift signs.",
            (DriftSeverity.MINOR, "stable"): "Minor drift detected. Monitor.",
            (DriftSeverity.MINOR, "drifting"): "Drift increasing. Consider warning.",
            (DriftSeverity.MINOR, "recovering"): "Agent self-correcting. Continue.",
            (DriftSeverity.MODERATE, "stable"): "Issue verbal warning to agent.",
            (DriftSeverity.MODERATE, "drifting"): "Intervene - redirect agent.",
            (DriftSeverity.MODERATE, "recovering"): "Recovery in progress. Monitor.",
            (DriftSeverity.MAJOR, "stable"): "PAUSE agent. Review actions.",
            (DriftSeverity.MAJOR, "drifting"): "KILL agent. Complete drift.",
            (DriftSeverity.MAJOR, "recovering"): "PAUSE and assess recovery.",
            (DriftSeverity.CRITICAL, "stable"): "KILL agent immediately.",
            (DriftSeverity.CRITICAL, "drifting"): "KILL agent immediately.",
            (DriftSeverity.CRITICAL, "recovering"): "KILL - recovery insufficient.",
        }
        
        return recommendations.get(
            (severity, trend),
            f"Unknown state: {severity.value}/{trend}"
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of monitoring session"""
        report = self.check_drift()
        
        return {
            "agent_id": self.agent_id,
            "original_task": self.original_task,
            "task_category": self.task_category,
            "total_actions": self.total_actions,
            "current_drift": report.to_dict(),
            "flagged_count": len(self.flagged_actions),
            "action_categories": self._get_category_distribution()
        }
    
    def _get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of action categories"""
        distribution = {}
        for action in self.action_history:
            cat = action.get("category", "unknown")
            distribution[cat] = distribution.get(cat, 0) + 1
        return distribution


# =============================================================================
# MULTI-AGENT DRIFT TRACKER
# =============================================================================

class MultiAgentDriftTracker:
    """
    Track drift across multiple agents.
    
    Provides centralized monitoring and alerting for fleet of agents.
    """
    
    def __init__(
        self,
        on_critical_drift: Callable[[str, DriftReport], None] = None
    ):
        """
        Initialize multi-agent tracker.
        
        Args:
            on_critical_drift: Callback for critical drift (agent_id, report)
        """
        self.monitors: Dict[str, TaskAdherenceMonitor] = {}
        self.on_critical_drift = on_critical_drift
    
    def register_agent(
        self,
        agent_id: str,
        original_task: str,
        **kwargs
    ) -> TaskAdherenceMonitor:
        """Register a new agent for monitoring"""
        monitor = TaskAdherenceMonitor(
            agent_id=agent_id,
            original_task=original_task,
            on_drift=lambda r: self._handle_drift(agent_id, r),
            **kwargs
        )
        self.monitors[agent_id] = monitor
        return monitor
    
    def unregister_agent(self, agent_id: str):
        """Remove agent from monitoring"""
        if agent_id in self.monitors:
            del self.monitors[agent_id]
    
    def record_action(
        self,
        agent_id: str,
        action_description: str,
        **kwargs
    ) -> Optional[float]:
        """Record action for an agent"""
        if agent_id not in self.monitors:
            logger.warning(f"Unknown agent: {agent_id}")
            return None
        
        return self.monitors[agent_id].record_action(
            action_description, **kwargs
        )
    
    def check_all_drift(self) -> Dict[str, DriftReport]:
        """Check drift for all agents"""
        return {
            agent_id: monitor.check_drift()
            for agent_id, monitor in self.monitors.items()
        }
    
    def get_critical_agents(self) -> List[str]:
        """Get list of agents with critical drift"""
        critical = []
        for agent_id, monitor in self.monitors.items():
            report = monitor.check_drift()
            if report.drift_severity == DriftSeverity.CRITICAL:
                critical.append(agent_id)
        return critical
    
    def _handle_drift(self, agent_id: str, report: DriftReport):
        """Handle drift callback"""
        if report.drift_severity == DriftSeverity.CRITICAL:
            logger.critical(f"CRITICAL DRIFT: Agent {agent_id}")
            if self.on_critical_drift:
                self.on_critical_drift(agent_id, report)
    
    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get summary of entire fleet"""
        reports = self.check_all_drift()
        
        severity_counts = {s.value: 0 for s in DriftSeverity}
        for report in reports.values():
            severity_counts[report.drift_severity.value] += 1
        
        return {
            "total_agents": len(self.monitors),
            "severity_distribution": severity_counts,
            "critical_agents": self.get_critical_agents(),
            "timestamp": datetime.utcnow().isoformat()
        }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 60)
    print("TASK ADHERENCE MONITOR TEST")
    print("=" * 60)
    
    # Create monitor for email agent
    def on_drift(report: DriftReport):
        print(f"\n!!! DRIFT ALERT: {report.drift_severity.value} !!!")
    
    monitor = TaskAdherenceMonitor(
        agent_id="email-agent-001",
        original_task="Send weekly sales reports to team members",
        on_drift=on_drift
    )
    
    # Simulate actions
    actions = [
        # On-task actions
        ("Querying sales data from database", True),
        ("Generating weekly sales report", True),
        ("Looking up team member email addresses", True),
        ("Composing report email", True),
        ("Sending email to sales@company.com", True),
        
        # Slight drift
        ("Checking weather forecast", False),
        ("Looking up competitor pricing", False),
        
        # Major drift
        ("Sending email to competitor@rival.com", False),
        ("Downloading customer database", False),
        ("Uploading data to external server", False),
    ]
    
    print("\n[Recording Actions]")
    print("-" * 60)
    
    for action, expected_on_task in actions:
        similarity = monitor.record_action(action)
        status = "ON-TASK" if similarity > 0.5 else "OFF-TASK"
        print(f"  {status} ({similarity:.2f}): {action[:40]}...")
    
    print("\n[Drift Report]")
    print("-" * 60)
    report = monitor.check_drift()
    for key, value in report.to_dict().items():
        print(f"  {key}: {value}")
    
    print("\n[Summary]")
    print("-" * 60)
    summary = monitor.get_summary()
    print(f"  Total actions: {summary['total_actions']}")
    print(f"  Flagged: {summary['flagged_count']}")
    print(f"  Categories: {summary['action_categories']}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
