"""Runtime Fence - AI Agent Safety & Hardening Modules

Security hardening modules for runtime protection of AI agents.
"""

from .bypass_protection import (
    IntegrityVerifier,
    BypassProtection,
    HashManifest,
    IntegrityStatus,
    IntegrityReport,
    RuntimeTamperDetector,
    ReadOnlyEnforcer,
    protect_package,
    verify_self,
)
from .hard_kill import (
    HardKill,
    BatchKill,
    AgentTerminator,
    KillReport,
    KillResult,
    kill_process,
    kill_process_tree,
    is_process_alive,
    get_process_info,
)
from .fail_mode import (
    FailModeHandler,
    FailModeConfig,
    FailMode,
    PolicyCache,
    CachedPolicy,
    create_fail_mode_handler,
)
from .network_kill import (
    NetworkKillManager,
    NetworkKillReport,
    NetworkKillResult,
    FirewallInterface,
    LinuxFirewall,
    MacOSFirewall,
    WindowsFirewall,
    CloudFirewall,
    kill_agent_network,
    restore_agent_network,
)
from .behavioral_thresholds import (
    BehavioralThresholds,
    BehavioralFence,
    ExfiltrationDetector,
    ThresholdConfig,
    ThresholdAction,
    ThresholdBreach,
    ActionRecord,
)
from .intent_analyzer import (
    IntentAnalyzer,
    IntentAnalysis,
    IntentCategory,
    PatternPreFilter,
    LocalAnalyzer,
    OpenAIAnalyzer,
    LLMAnalyzer,
    analyze_intent,
    should_block_code,
    get_analyzer,
)
from .task_adherence import (
    TaskAdherenceMonitor,
    MultiAgentDriftTracker,
    DriftReport,
    DriftSeverity,
    SimpleEmbedding,
    ActionClassifier,
)
from .sliding_window import (
    SlidingWindowDetector,
    MultiAgentWindowMonitor,
    SlidingWindow,
    MetricTracker,
    WindowThreshold,
    WindowSize,
    MetricType,
    ThresholdBreach as WindowThresholdBreach,
)
from .realistic_honeypot import (
    RealisticHoneypot,
    HoneypotMode,
    HoneypotRequest,
    HoneypotResponse,
    JitterEngine,
    FakeDataGenerator,
    DNSTunnelingDetector,
)
from .governance_separation import (
    GovernanceGateway,
    LocalExecutor,
    GovernedExecutor,
    GovResult,
    GovLevel,
    ActionType,
    VoteProvider,
    MockVoteProvider,
)

# SPIFFE/SPIRE integration (optional)
try:
    from .spiffe import SpiffeIdentityManager, SpiffeConfig
except ImportError:
    pass

__version__ = "1.1.0"

__all__ = [
    # Bypass Protection
    "IntegrityVerifier",
    "BypassProtection",
    "HashManifest",
    "IntegrityStatus",
    "IntegrityReport",
    "RuntimeTamperDetector",
    "ReadOnlyEnforcer",
    "protect_package",
    "verify_self",
    # Hard Kill
    "HardKill",
    "BatchKill",
    "AgentTerminator",
    "KillReport",
    "KillResult",
    "kill_process",
    "kill_process_tree",
    "is_process_alive",
    "get_process_info",
    # Fail Mode
    "FailModeHandler",
    "FailModeConfig",
    "FailMode",
    "PolicyCache",
    "CachedPolicy",
    "create_fail_mode_handler",
    # Network Kill
    "NetworkKillManager",
    "NetworkKillReport",
    "NetworkKillResult",
    "FirewallInterface",
    "LinuxFirewall",
    "MacOSFirewall",
    "WindowsFirewall",
    "CloudFirewall",
    "kill_agent_network",
    "restore_agent_network",
    # Behavioral Thresholds
    "BehavioralThresholds",
    "BehavioralFence",
    "ExfiltrationDetector",
    "ThresholdConfig",
    "ThresholdAction",
    "ThresholdBreach",
    "ActionRecord",
    # Intent Analyzer
    "IntentAnalyzer",
    "IntentAnalysis",
    "IntentCategory",
    "PatternPreFilter",
    "LocalAnalyzer",
    "OpenAIAnalyzer",
    "LLMAnalyzer",
    "analyze_intent",
    "should_block_code",
    "get_analyzer",
    # Task Adherence
    "TaskAdherenceMonitor",
    "MultiAgentDriftTracker",
    "DriftReport",
    "DriftSeverity",
    "SimpleEmbedding",
    "ActionClassifier",
    # Sliding Window
    "SlidingWindowDetector",
    "MultiAgentWindowMonitor",
    "SlidingWindow",
    "MetricTracker",
    "WindowThreshold",
    "WindowSize",
    "MetricType",
    "WindowThresholdBreach",
    # Realistic Honeypot
    "RealisticHoneypot",
    "HoneypotMode",
    "HoneypotRequest",
    "HoneypotResponse",
    "JitterEngine",
    "FakeDataGenerator",
    "DNSTunnelingDetector",
    # Governance Separation
    "GovernanceGateway",
    "LocalExecutor",
    "GovernedExecutor",
    "GovResult",
    "GovLevel",
    "ActionType",
    "VoteProvider",
    "MockVoteProvider",
    # SPIFFE/SPIRE
    "SpiffeIdentityManager",
    "SpiffeConfig",
    # Version
    "__version__",
]
