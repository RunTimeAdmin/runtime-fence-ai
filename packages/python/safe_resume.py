"""
Runtime Fence - Safe Resume
Controlled recovery after kill switch activation.
"""

import time
import logging
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fence_resume")


class ResumeMode(Enum):
    IMMEDIATE = "immediate"      # Resume right away (admin only)
    COOLDOWN = "cooldown"        # Wait for cooldown period
    APPROVAL = "approval"        # Require manual approval
    GRADUAL = "gradual"          # Gradually restore permissions


@dataclass
class ResumePolicy:
    """Policy for resuming after kill switch."""
    mode: ResumeMode = ResumeMode.COOLDOWN
    cooldown_seconds: int = 300  # 5 minutes default
    require_reason: bool = True
    require_approval: bool = False
    approver_id: Optional[str] = None
    gradual_steps: int = 3
    gradual_interval: int = 60  # seconds between steps
    max_resumes_per_hour: int = 3
    blocked_after_resume: list = None  # Actions to keep blocked
    
    def __post_init__(self):
        if self.blocked_after_resume is None:
            self.blocked_after_resume = []


class ResumeManager:
    """Manages safe resume after kill switch activation."""
    
    def __init__(self, policy: ResumePolicy = None):
        self.policy = policy or ResumePolicy()
        self.kill_history: list = []
        self.resume_history: list = []
        self.pending_approvals: Dict[str, dict] = {}
        self.gradual_state: Dict[str, dict] = {}
        self.approval_callback: Optional[Callable] = None
    
    def record_kill(self, agent_id: str, reason: str, triggered_by: str = "system"):
        """Record a kill switch activation."""
        self.kill_history.append({
            "agent_id": agent_id,
            "reason": reason,
            "triggered_by": triggered_by,
            "timestamp": time.time(),
            "resumed": False
        })
        logger.critical(f"Kill switch recorded: {agent_id} - {reason}")
    
    def can_resume(self, agent_id: str, user_id: str = None) -> tuple[bool, str]:
        """
        Check if an agent can be resumed.
        Returns (can_resume, reason).
        """
        # Find most recent kill for this agent
        agent_kills = [k for k in self.kill_history if k["agent_id"] == agent_id and not k["resumed"]]
        
        if not agent_kills:
            return True, "No active kill switch"
        
        last_kill = agent_kills[-1]
        kill_time = last_kill["timestamp"]
        
        # Check cooldown
        if self.policy.mode == ResumeMode.COOLDOWN:
            elapsed = time.time() - kill_time
            if elapsed < self.policy.cooldown_seconds:
                remaining = int(self.policy.cooldown_seconds - elapsed)
                return False, f"Cooldown active: {remaining} seconds remaining"
        
        # Check approval requirement
        if self.policy.mode == ResumeMode.APPROVAL or self.policy.require_approval:
            if agent_id not in self.pending_approvals:
                return False, "Approval required to resume"
            
            approval = self.pending_approvals[agent_id]
            if not approval.get("approved"):
                return False, "Awaiting approval"
        
        # Check resume rate limit
        recent_resumes = [
            r for r in self.resume_history
            if r["agent_id"] == agent_id and 
            time.time() - r["timestamp"] < 3600  # Last hour
        ]
        if len(recent_resumes) >= self.policy.max_resumes_per_hour:
            return False, f"Rate limit: max {self.policy.max_resumes_per_hour} resumes per hour"
        
        return True, "Resume allowed"
    
    def request_resume(
        self,
        agent_id: str,
        user_id: str,
        reason: str
    ) -> dict:
        """
        Request to resume an agent after kill switch.
        Returns status of the request.
        """
        can_resume, message = self.can_resume(agent_id, user_id)
        
        if can_resume and self.policy.mode == ResumeMode.IMMEDIATE:
            # Immediate resume
            return self._execute_resume(agent_id, user_id, reason)
        
        if self.policy.mode == ResumeMode.COOLDOWN and can_resume:
            # Resume after cooldown
            return self._execute_resume(agent_id, user_id, reason)
        
        if self.policy.mode == ResumeMode.APPROVAL:
            # Create approval request
            self.pending_approvals[agent_id] = {
                "requested_by": user_id,
                "reason": reason,
                "timestamp": time.time(),
                "approved": False,
                "approver": None
            }
            
            # Notify approver if callback is set
            if self.approval_callback:
                self.approval_callback(agent_id, user_id, reason)
            
            return {
                "status": "pending_approval",
                "agent_id": agent_id,
                "message": "Resume request submitted for approval"
            }
        
        if self.policy.mode == ResumeMode.GRADUAL:
            # Start gradual resume
            return self._start_gradual_resume(agent_id, user_id, reason)
        
        return {
            "status": "blocked",
            "agent_id": agent_id,
            "message": message
        }
    
    def approve_resume(self, agent_id: str, approver_id: str) -> dict:
        """Approve a pending resume request."""
        if agent_id not in self.pending_approvals:
            return {"status": "error", "message": "No pending approval for this agent"}
        
        # Check if approver is authorized
        if self.policy.approver_id and approver_id != self.policy.approver_id:
            return {"status": "error", "message": "Not authorized to approve"}
        
        approval = self.pending_approvals[agent_id]
        approval["approved"] = True
        approval["approver"] = approver_id
        approval["approved_at"] = time.time()
        
        # Execute the resume
        return self._execute_resume(
            agent_id,
            approval["requested_by"],
            approval["reason"]
        )
    
    def deny_resume(self, agent_id: str, approver_id: str, reason: str = None) -> dict:
        """Deny a pending resume request."""
        if agent_id in self.pending_approvals:
            del self.pending_approvals[agent_id]
        
        return {
            "status": "denied",
            "agent_id": agent_id,
            "denied_by": approver_id,
            "reason": reason
        }
    
    def _execute_resume(self, agent_id: str, user_id: str, reason: str) -> dict:
        """Execute the actual resume."""
        # Mark kill as resumed
        for kill in self.kill_history:
            if kill["agent_id"] == agent_id and not kill["resumed"]:
                kill["resumed"] = True
                kill["resumed_at"] = time.time()
                kill["resumed_by"] = user_id
        
        # Record resume
        resume_record = {
            "agent_id": agent_id,
            "user_id": user_id,
            "reason": reason,
            "timestamp": time.time(),
            "blocked_actions": self.policy.blocked_after_resume.copy()
        }
        self.resume_history.append(resume_record)
        
        # Clean up pending approval
        if agent_id in self.pending_approvals:
            del self.pending_approvals[agent_id]
        
        logger.info(f"Agent resumed: {agent_id} by {user_id}")
        
        return {
            "status": "resumed",
            "agent_id": agent_id,
            "resumed_by": user_id,
            "blocked_actions": self.policy.blocked_after_resume,
            "message": "Agent has been resumed with restricted permissions" if self.policy.blocked_after_resume else "Agent has been fully resumed"
        }
    
    def _start_gradual_resume(self, agent_id: str, user_id: str, reason: str) -> dict:
        """Start a gradual resume process."""
        self.gradual_state[agent_id] = {
            "user_id": user_id,
            "reason": reason,
            "started_at": time.time(),
            "current_step": 0,
            "total_steps": self.policy.gradual_steps,
            "next_step_at": time.time() + self.policy.gradual_interval
        }
        
        logger.info(f"Starting gradual resume for {agent_id}: step 1/{self.policy.gradual_steps}")
        
        return {
            "status": "gradual_resume_started",
            "agent_id": agent_id,
            "current_step": 1,
            "total_steps": self.policy.gradual_steps,
            "next_step_in": self.policy.gradual_interval,
            "message": f"Gradual resume started. Permissions will be restored over {self.policy.gradual_steps} steps."
        }
    
    def get_gradual_permissions(self, agent_id: str) -> dict:
        """Get current permissions during gradual resume."""
        if agent_id not in self.gradual_state:
            return {"full_access": True}
        
        state = self.gradual_state[agent_id]
        
        # Check if time to advance step
        if time.time() >= state["next_step_at"]:
            state["current_step"] += 1
            state["next_step_at"] = time.time() + self.policy.gradual_interval
            
            if state["current_step"] >= state["total_steps"]:
                # Gradual resume complete
                del self.gradual_state[agent_id]
                self._execute_resume(agent_id, state["user_id"], state["reason"])
                return {"full_access": True}
        
        # Return restricted permissions based on step
        step_ratio = state["current_step"] / state["total_steps"]
        
        return {
            "full_access": False,
            "step": state["current_step"],
            "total_steps": state["total_steps"],
            "permission_level": step_ratio,
            "allowed_risk_threshold": int(25 + (75 * step_ratio)),  # 25% -> 100%
            "spending_limit_multiplier": step_ratio  # 0% -> 100% of original
        }
    
    def get_status(self, agent_id: str = None) -> dict:
        """Get resume status for an agent or all agents."""
        if agent_id:
            active_kills = [k for k in self.kill_history if k["agent_id"] == agent_id and not k["resumed"]]
            gradual = self.gradual_state.get(agent_id)
            pending = self.pending_approvals.get(agent_id)
            
            return {
                "agent_id": agent_id,
                "is_killed": len(active_kills) > 0,
                "last_kill": active_kills[-1] if active_kills else None,
                "pending_approval": pending,
                "gradual_resume": gradual,
                "can_resume": self.can_resume(agent_id)
            }
        
        return {
            "active_kills": [k for k in self.kill_history if not k["resumed"]],
            "pending_approvals": list(self.pending_approvals.keys()),
            "gradual_resumes": list(self.gradual_state.keys()),
            "total_kills": len(self.kill_history),
            "total_resumes": len(self.resume_history)
        }


# Global resume manager
_resume_manager: Optional[ResumeManager] = None

def get_resume_manager() -> ResumeManager:
    global _resume_manager
    if _resume_manager is None:
        _resume_manager = ResumeManager()
    return _resume_manager

def configure_resume(policy: ResumePolicy):
    global _resume_manager
    _resume_manager = ResumeManager(policy)
