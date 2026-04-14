"""
Hard Kill - Escalating Process Termination

This module implements escalating kill strategies to ensure agent processes
are truly terminated, even when unresponsive to soft signals.

Kill Sequence:
1. SIGTERM (soft) - Give process chance to cleanup
2. Wait 2 seconds - Allow graceful shutdown
3. Check if alive - Verify termination
4. SIGKILL (hard) - Force termination if still alive
5. Verify death - Confirm process is gone

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import os
import sys
import time
import signal
import logging
import subprocess
import platform
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# KILL RESULT TYPES
# =============================================================================

class KillResult(Enum):
    """Result of a kill operation"""
    SUCCESS = "success"              # Process terminated successfully
    ALREADY_DEAD = "already_dead"    # Process was not running
    SOFT_KILL_SUCCESS = "soft"       # Terminated via SIGTERM
    HARD_KILL_SUCCESS = "hard"       # Required SIGKILL
    FAILED = "failed"                # Could not terminate
    PERMISSION_DENIED = "denied"     # Insufficient permissions
    ZOMBIE = "zombie"                # Process is zombie (can't be killed)


@dataclass
class KillReport:
    """
    Detailed report of a kill operation.
    
    Attributes:
        pid: Process ID that was targeted
        result: The kill result status
        soft_signal_sent: Whether SIGTERM was sent
        hard_signal_sent: Whether SIGKILL was sent
        time_to_death_ms: Milliseconds until process terminated
        error: Error message if failed
        timestamp: When the kill was attempted
    """
    pid: int
    result: KillResult
    soft_signal_sent: bool = False
    hard_signal_sent: bool = False
    time_to_death_ms: Optional[float] = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "result": self.result.value,
            "soft_signal_sent": self.soft_signal_sent,
            "hard_signal_sent": self.hard_signal_sent,
            "time_to_death_ms": self.time_to_death_ms,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# PROCESS UTILITIES
# =============================================================================

def is_process_alive(pid: int) -> bool:
    """
    Check if a process is still running.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process is running, False otherwise
    """
    if platform.system() == "Windows":
        return _is_alive_windows(pid)
    else:
        return _is_alive_unix(pid)


def _is_alive_unix(pid: int) -> bool:
    """Check if process is alive on Unix/Linux/macOS"""
    try:
        # Signal 0 doesn't kill, just checks if process exists
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission
        return True


def _is_alive_windows(pid: int) -> bool:
    """Check if process is alive on Windows"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """
    Get information about a process.
    
    Args:
        pid: Process ID
        
    Returns:
        Dict with process info, or None if not found
    """
    if platform.system() == "Windows":
        return _get_info_windows(pid)
    else:
        return _get_info_unix(pid)


def _get_info_unix(pid: int) -> Optional[Dict[str, Any]]:
    """Get process info on Unix"""
    try:
        result = subprocess.run(
            ['ps', '-p', str(pid), '-o', 'pid,ppid,user,comm,state'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                return {
                    'pid': int(parts[0]),
                    'ppid': int(parts[1]) if len(parts) > 1 else None,
                    'user': parts[2] if len(parts) > 2 else None,
                    'command': parts[3] if len(parts) > 3 else None,
                    'state': parts[4] if len(parts) > 4 else None
                }
    except Exception:
        pass
    return None


def _get_info_windows(pid: int) -> Optional[Dict[str, Any]]:
    """Get process info on Windows"""
    try:
        result = subprocess.run(
            ['wmic', 'process', 'where', f'ProcessId={pid}', 'get',
             'ProcessId,ParentProcessId,Name,Status', '/format:list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info = {}
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    info[key.lower()] = value
            if info:
                return {
                    'pid': int(info.get('processid', 0)),
                    'ppid': int(info.get('parentprocessid', 0)),
                    'command': info.get('name'),
                    'state': info.get('status', 'running')
                }
    except Exception:
        pass
    return None


# =============================================================================
# HARD KILL IMPLEMENTATION
# =============================================================================

class HardKill:
    """
    Implements escalating kill strategy for process termination.
    
    This class provides reliable process termination through:
    1. Soft kill attempt (SIGTERM)
    2. Wait period for graceful shutdown
    3. Hard kill if still alive (SIGKILL)
    4. Verification of termination
    
    Usage:
        killer = HardKill()
        report = killer.kill(pid)
        if report.result == KillResult.SUCCESS:
            print("Process terminated")
    """
    
    def __init__(
        self,
        soft_timeout_seconds: float = 2.0,
        verify_interval_ms: float = 100,
        max_verify_attempts: int = 10
    ):
        """
        Initialize HardKill with configuration.
        
        Args:
            soft_timeout_seconds: How long to wait after SIGTERM before SIGKILL
            verify_interval_ms: How often to check if process died
            max_verify_attempts: Max times to verify after SIGKILL
        """
        self.soft_timeout = soft_timeout_seconds
        self.verify_interval = verify_interval_ms / 1000.0
        self.max_verify_attempts = max_verify_attempts
        self.os_type = platform.system()
        
        logger.info(f"HardKill initialized (OS: {self.os_type})")
    
    def kill(self, pid: int, escalate: bool = True) -> KillReport:
        """
        Kill a process with optional escalation.
        
        Args:
            pid: Process ID to terminate
            escalate: If True, use SIGKILL if SIGTERM fails
            
        Returns:
            KillReport with details of the operation
        """
        start_time = time.time()
        
        logger.info(f"Initiating kill for PID {pid} (escalate={escalate})")
        
        # Step 1: Check if process exists
        if not is_process_alive(pid):
            logger.info(f"PID {pid} is not running (already dead)")
            return KillReport(
                pid=pid,
                result=KillResult.ALREADY_DEAD,
                time_to_death_ms=0
            )
        
        # Step 2: Send soft kill (SIGTERM)
        soft_success = self._send_soft_kill(pid)
        
        if not soft_success:
            # Couldn't send signal - likely permission issue
            return KillReport(
                pid=pid,
                result=KillResult.PERMISSION_DENIED,
                soft_signal_sent=False,
                error="Failed to send SIGTERM - check permissions"
            )
        
        # Step 3: Wait and check if dead
        if self._wait_for_death(pid, self.soft_timeout):
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"PID {pid} terminated gracefully in {elapsed_ms:.0f}ms")
            return KillReport(
                pid=pid,
                result=KillResult.SOFT_KILL_SUCCESS,
                soft_signal_sent=True,
                time_to_death_ms=elapsed_ms
            )
        
        # Process still alive after soft timeout
        if not escalate:
            logger.warning(f"PID {pid} did not respond to SIGTERM (escalation disabled)")
            return KillReport(
                pid=pid,
                result=KillResult.FAILED,
                soft_signal_sent=True,
                error="Process did not respond to SIGTERM and escalation is disabled"
            )
        
        # Step 4: Escalate to hard kill (SIGKILL)
        logger.warning(f"PID {pid} did not respond to SIGTERM, escalating to SIGKILL")
        
        hard_success = self._send_hard_kill(pid)
        
        if not hard_success:
            return KillReport(
                pid=pid,
                result=KillResult.FAILED,
                soft_signal_sent=True,
                hard_signal_sent=False,
                error="Failed to send SIGKILL"
            )
        
        # Step 5: Verify death after hard kill
        if self._verify_death(pid):
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"PID {pid} terminated via SIGKILL in {elapsed_ms:.0f}ms")
            return KillReport(
                pid=pid,
                result=KillResult.HARD_KILL_SUCCESS,
                soft_signal_sent=True,
                hard_signal_sent=True,
                time_to_death_ms=elapsed_ms
            )
        
        # Process survived SIGKILL - likely a zombie
        elapsed_ms = (time.time() - start_time) * 1000
        logger.critical(f"PID {pid} survived SIGKILL - possible zombie process!")
        return KillReport(
            pid=pid,
            result=KillResult.ZOMBIE,
            soft_signal_sent=True,
            hard_signal_sent=True,
            time_to_death_ms=elapsed_ms,
            error="Process survived SIGKILL - may be zombie or kernel-protected"
        )
    
    def _send_soft_kill(self, pid: int) -> bool:
        """Send SIGTERM (soft kill) to process"""
        try:
            if self.os_type == "Windows":
                # Windows doesn't have SIGTERM, use taskkill without /F
                result = subprocess.run(
                    ['taskkill', '/PID', str(pid)],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            else:
                os.kill(pid, signal.SIGTERM)
                logger.debug(f"Sent SIGTERM to PID {pid}")
                return True
        except ProcessLookupError:
            # Process already dead
            return True
        except PermissionError:
            logger.error(f"Permission denied sending SIGTERM to PID {pid}")
            return False
        except Exception as e:
            logger.error(f"Error sending SIGTERM to PID {pid}: {e}")
            return False
    
    def _send_hard_kill(self, pid: int) -> bool:
        """Send SIGKILL (hard kill) to process"""
        try:
            if self.os_type == "Windows":
                # Windows: taskkill /F forces termination
                result = subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid)],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            else:
                os.kill(pid, signal.SIGKILL)
                logger.debug(f"Sent SIGKILL to PID {pid}")
                return True
        except ProcessLookupError:
            # Process already dead
            return True
        except PermissionError:
            logger.error(f"Permission denied sending SIGKILL to PID {pid}")
            return False
        except Exception as e:
            logger.error(f"Error sending SIGKILL to PID {pid}: {e}")
            return False
    
    def _wait_for_death(self, pid: int, timeout: float) -> bool:
        """Wait for process to die within timeout"""
        start = time.time()
        while time.time() - start < timeout:
            if not is_process_alive(pid):
                return True
            time.sleep(self.verify_interval)
        return False
    
    def _verify_death(self, pid: int) -> bool:
        """Verify process is truly dead after hard kill"""
        for _ in range(self.max_verify_attempts):
            if not is_process_alive(pid):
                return True
            time.sleep(self.verify_interval)
        return not is_process_alive(pid)


# =============================================================================
# BATCH KILL
# =============================================================================

class BatchKill:
    """
    Kill multiple processes, optionally with parent-child awareness.
    
    Use this to terminate an agent and all its child processes.
    """
    
    def __init__(self, hard_kill: HardKill = None):
        self.killer = hard_kill or HardKill()
        self.os_type = platform.system()
    
    def kill_tree(self, pid: int) -> List[KillReport]:
        """
        Kill a process and all its descendants.
        
        Args:
            pid: Root process ID
            
        Returns:
            List of KillReports for each process killed
        """
        reports = []
        
        # Get all child PIDs
        children = self._get_children(pid)
        
        # Kill children first (bottom-up)
        for child_pid in reversed(children):
            report = self.killer.kill(child_pid)
            reports.append(report)
        
        # Kill parent last
        report = self.killer.kill(pid)
        reports.append(report)
        
        return reports
    
    def kill_many(self, pids: List[int]) -> List[KillReport]:
        """
        Kill multiple unrelated processes.
        
        Args:
            pids: List of process IDs to kill
            
        Returns:
            List of KillReports
        """
        return [self.killer.kill(pid) for pid in pids]
    
    def _get_children(self, pid: int) -> List[int]:
        """Get all child process IDs recursively"""
        children = []
        
        if self.os_type == "Windows":
            children = self._get_children_windows(pid)
        else:
            children = self._get_children_unix(pid)
        
        return children
    
    def _get_children_unix(self, pid: int) -> List[int]:
        """Get child PIDs on Unix"""
        children = []
        try:
            result = subprocess.run(
                ['pgrep', '-P', str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        child_pid = int(line)
                        children.append(child_pid)
                        # Recursively get grandchildren
                        children.extend(self._get_children_unix(child_pid))
        except Exception:
            pass
        return children
    
    def _get_children_windows(self, pid: int) -> List[int]:
        """Get child PIDs on Windows"""
        children = []
        try:
            result = subprocess.run(
                ['wmic', 'process', 'where', f'ParentProcessId={pid}',
                 'get', 'ProcessId', '/format:list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'ProcessId=' in line:
                        child_pid = int(line.split('=')[1].strip())
                        children.append(child_pid)
                        # Recursively get grandchildren
                        children.extend(self._get_children_windows(child_pid))
        except Exception:
            pass
        return children


# =============================================================================
# AGENT TERMINATOR
# =============================================================================

class AgentTerminator:
    """
    High-level interface for terminating AI agents.
    
    Provides:
    - PID tracking for registered agents
    - Kill by agent ID or PID
    - Emergency kill all
    - Kill reports and logging
    
    Usage:
        terminator = AgentTerminator()
        
        # Register agent
        terminator.register_agent("agent-123", pid=12345)
        
        # Kill by agent ID
        report = terminator.kill_agent("agent-123")
        
        # Emergency: kill all
        reports = terminator.kill_all()
    """
    
    def __init__(self):
        self.hard_kill = HardKill()
        self.batch_kill = BatchKill(self.hard_kill)
        self._agents: Dict[str, int] = {}  # agent_id -> pid
        self._kill_history: List[KillReport] = []
    
    def register_agent(self, agent_id: str, pid: int):
        """Register an agent's PID for tracking"""
        self._agents[agent_id] = pid
        logger.info(f"Registered agent {agent_id} with PID {pid}")
    
    def unregister_agent(self, agent_id: str):
        """Remove agent from tracking"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
    
    def kill_agent(self, agent_id: str, kill_children: bool = True) -> Optional[KillReport]:
        """
        Kill an agent by its ID.
        
        Args:
            agent_id: The agent's ID
            kill_children: Whether to kill child processes too
            
        Returns:
            KillReport if agent was registered, None otherwise
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not registered")
            return None
        
        pid = self._agents[agent_id]
        
        if kill_children:
            reports = self.batch_kill.kill_tree(pid)
            # Return the parent's report (last one)
            report = reports[-1] if reports else None
        else:
            report = self.hard_kill.kill(pid)
        
        if report:
            self._kill_history.append(report)
            self.unregister_agent(agent_id)
        
        return report
    
    def kill_by_pid(self, pid: int, kill_children: bool = True) -> KillReport:
        """
        Kill a process by PID directly.
        
        Args:
            pid: Process ID to kill
            kill_children: Whether to kill child processes too
            
        Returns:
            KillReport
        """
        if kill_children:
            reports = self.batch_kill.kill_tree(pid)
            report = reports[-1] if reports else KillReport(
                pid=pid,
                result=KillResult.FAILED,
                error="No reports generated"
            )
        else:
            report = self.hard_kill.kill(pid)
        
        self._kill_history.append(report)
        
        # Remove from agents if registered
        for agent_id, agent_pid in list(self._agents.items()):
            if agent_pid == pid:
                self.unregister_agent(agent_id)
                break
        
        return report
    
    def kill_all(self) -> List[KillReport]:
        """
        Emergency: Kill ALL registered agents.
        
        Returns:
            List of KillReports for all terminations
        """
        logger.critical("🚨 EMERGENCY KILL ALL INITIATED")
        
        reports = []
        for agent_id in list(self._agents.keys()):
            report = self.kill_agent(agent_id, kill_children=True)
            if report:
                reports.append(report)
        
        logger.critical(f"Killed {len(reports)} agents")
        return reports
    
    def get_registered_agents(self) -> Dict[str, int]:
        """Get all registered agent IDs and PIDs"""
        return dict(self._agents)
    
    def get_kill_history(self) -> List[Dict[str, Any]]:
        """Get history of all kill operations"""
        return [r.to_dict() for r in self._kill_history]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def kill_process(pid: int, escalate: bool = True) -> KillReport:
    """
    Convenience function to kill a single process.
    
    Args:
        pid: Process ID to terminate
        escalate: Whether to use SIGKILL if SIGTERM fails
        
    Returns:
        KillReport with operation details
    """
    killer = HardKill()
    return killer.kill(pid, escalate)


def kill_process_tree(pid: int) -> List[KillReport]:
    """
    Convenience function to kill a process and all its children.
    
    Args:
        pid: Root process ID
        
    Returns:
        List of KillReports
    """
    batch = BatchKill()
    return batch.kill_tree(pid)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hard Kill - Escalating Process Termination")
    parser.add_argument("pid", type=int, help="Process ID to kill")
    parser.add_argument("--no-escalate", action="store_true", help="Don't escalate to SIGKILL")
    parser.add_argument("--tree", action="store_true", help="Kill process tree")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    if args.tree:
        reports = kill_process_tree(args.pid)
        for report in reports:
            print(f"PID {report.pid}: {report.result.value}")
    else:
        report = kill_process(args.pid, escalate=not args.no_escalate)
        print(f"PID {report.pid}: {report.result.value}")
        if report.error:
            print(f"Error: {report.error}")
        if report.time_to_death_ms:
            print(f"Time to death: {report.time_to_death_ms:.0f}ms")
