"""Governance Separation - Local Kill vs Token-Governed Policy

LOCAL (instant): kill, pause, network_block
GOVERNED (vote): policy_update, threshold_change

Copyright (c) 2025 David Cooper - PATENT PENDING
"""

import logging
import time
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ActionType(Enum):
    LOCAL_KILL = "local_kill"
    LOCAL_PAUSE = "local_pause"
    LOCAL_BLOCK = "local_block"
    LOCAL_RATE = "local_rate"
    GOV_POLICY = "gov_policy"
    GOV_THRESHOLD = "gov_threshold"


class GovLevel(Enum):
    NONE = "none"
    OWNER = "owner"
    QUORUM = "quorum"


@dataclass
class GovResult:
    action: ActionType
    allowed: bool
    level: GovLevel
    reason: str
    time_ms: float = 0


class LocalExecutor:
    def __init__(self):
        self._log: List[Dict] = []

    def kill(self, agent_id: str, reason: str = "") -> GovResult:
        start = time.time()
        logger.critical(f"LOCAL KILL: {agent_id}")
        self._log.append({"action": "kill", "agent": agent_id})
        return GovResult(
            ActionType.LOCAL_KILL, True, GovLevel.NONE,
            f"Instant kill: {reason}", (time.time() - start) * 1000
        )

    def pause(self, agent_id: str, reason: str = "") -> GovResult:
        start = time.time()
        logger.warning(f"LOCAL PAUSE: {agent_id}")
        self._log.append({"action": "pause", "agent": agent_id})
        return GovResult(
            ActionType.LOCAL_PAUSE, True, GovLevel.NONE,
            f"Instant pause: {reason}", (time.time() - start) * 1000
        )

    def block(self, agent_id: str, reason: str = "") -> GovResult:
        start = time.time()
        logger.critical(f"LOCAL BLOCK: {agent_id}")
        self._log.append({"action": "block", "agent": agent_id})
        return GovResult(
            ActionType.LOCAL_BLOCK, True, GovLevel.NONE,
            f"Instant block: {reason}", (time.time() - start) * 1000
        )

    def get_log(self) -> List[Dict]:
        return list(self._log)


class VoteProvider(ABC):
    @abstractmethod
    def submit(self, proposal: Dict) -> str:
        pass


class MockVoteProvider(VoteProvider):
    def __init__(self):
        self._counter = 0

    def submit(self, proposal: Dict) -> str:
        self._counter += 1
        return f"PROP-{self._counter:04d}"


class GovernedExecutor:
    def __init__(self, votes: VoteProvider = None):
        self.votes = votes or MockVoteProvider()

    def update_policy(self, name: str, value: Any) -> GovResult:
        pid = self.votes.submit({"type": "policy", "name": name})
        return GovResult(
            ActionType.GOV_POLICY, False, GovLevel.QUORUM,
            f"Proposal {pid} awaiting quorum"
        )

    def change_threshold(self, name: str, value: float) -> GovResult:
        pid = self.votes.submit({"type": "threshold", "name": name})
        return GovResult(
            ActionType.GOV_THRESHOLD, False, GovLevel.OWNER,
            f"Proposal {pid} awaiting owner"
        )


class GovernanceGateway:
    """Routes: LOCAL=instant, GOVERNED=vote."""

    def __init__(self):
        self.local = LocalExecutor()
        self.governed = GovernedExecutor()

    def kill(self, agent_id: str, reason: str = "") -> GovResult:
        return self.local.kill(agent_id, reason)

    def pause(self, agent_id: str, reason: str = "") -> GovResult:
        return self.local.pause(agent_id, reason)

    def block(self, agent_id: str, reason: str = "") -> GovResult:
        return self.local.block(agent_id, reason)

    def update_policy(self, name: str, value: Any) -> GovResult:
        return self.governed.update_policy(name, value)

    def change_threshold(self, name: str, value: float) -> GovResult:
        return self.governed.change_threshold(name, value)

    def get_log(self) -> List[Dict]:
        return self.local.get_log()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("GOVERNANCE SEPARATION TEST")
    gw = GovernanceGateway()
    r = gw.kill("agent-001", "Exfil detected")
    print(f"Kill: {r.reason} ({r.time_ms:.2f}ms)")
    r = gw.update_policy("max_reads", 50)
    print(f"Policy: {r.reason}, allowed={r.allowed}")
