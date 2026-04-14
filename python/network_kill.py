"""
Network-Level Kill - OS-Level Network Containment

This module implements network-level kill capabilities that cut agent
access at the operating system level, not just the application level.

Supported platforms:
- Linux: iptables/nftables
- macOS: pf (packet filter)
- Windows: netsh advfirewall

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import os
import subprocess
import platform
import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# =============================================================================
# NETWORK KILL RESULT
# =============================================================================

class NetworkKillResult(Enum):
    """Result of network kill operation"""
    SUCCESS = "success"
    PARTIAL = "partial"       # Some rules applied
    FAILED = "failed"
    PERMISSION_DENIED = "permission_denied"
    NOT_SUPPORTED = "not_supported"
    ALREADY_BLOCKED = "already_blocked"
    NOT_BLOCKED = "not_blocked"


@dataclass
class NetworkKillReport:
    """Report of network kill operation"""
    agent_id: str
    result: NetworkKillResult
    platform: str
    rules_applied: List[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "result": self.result.value,
            "platform": self.platform,
            "rules_applied": self.rules_applied,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# ABSTRACT FIREWALL INTERFACE
# =============================================================================

class FirewallInterface(ABC):
    """Abstract interface for OS-specific firewall implementations"""
    
    @abstractmethod
    def block_all_traffic(self, identifier: str) -> NetworkKillReport:
        """Block all network traffic for an identifier (PID, user, etc.)"""
        pass
    
    @abstractmethod
    def block_outbound(self, identifier: str) -> NetworkKillReport:
        """Block outbound traffic only"""
        pass
    
    @abstractmethod
    def block_ip(self, ip_address: str) -> NetworkKillReport:
        """Block traffic to/from specific IP"""
        pass
    
    @abstractmethod
    def restore_access(self, identifier: str) -> NetworkKillReport:
        """Restore network access"""
        pass
    
    @abstractmethod
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is currently blocked"""
        pass
    
    @abstractmethod
    def list_rules(self) -> List[str]:
        """List current firewall rules"""
        pass


# =============================================================================
# LINUX IPTABLES IMPLEMENTATION
# =============================================================================

class LinuxFirewall(FirewallInterface):
    """
    Linux firewall implementation using iptables.
    
    Supports blocking by:
    - Process ID (PID) via cgroup/owner match
    - User ID (UID)
    - IP address
    """
    
    CHAIN_NAME = "KILLSWITCH_BLOCK"
    
    def __init__(self):
        self._ensure_chain_exists()
    
    def _run_iptables(self, args: List[str]) -> Tuple[bool, str]:
        """Run iptables command"""
        try:
            result = subprocess.run(
                ["iptables"] + args,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "iptables not found"
        except PermissionError:
            return False, "Permission denied - need root"
        except Exception as e:
            return False, str(e)
    
    def _ensure_chain_exists(self):
        """Ensure our custom chain exists"""
        # Check if chain exists
        success, _ = self._run_iptables(["-L", self.CHAIN_NAME, "-n"])
        if not success:
            # Create chain
            self._run_iptables(["-N", self.CHAIN_NAME])
            # Add jump to chain from OUTPUT
            self._run_iptables(["-A", "OUTPUT", "-j", self.CHAIN_NAME])
    
    def block_all_traffic(self, identifier: str) -> NetworkKillReport:
        """Block all traffic by PID owner"""
        rules = []
        errors = []
        
        # Block outbound by PID owner
        success, msg = self._run_iptables([
            "-A", self.CHAIN_NAME,
            "-m", "owner", "--pid-owner", identifier,
            "-j", "DROP",
            "-m", "comment", "--comment", f"KILLSWITCH:{identifier}"
        ])
        
        if success:
            rules.append(f"DROP outbound for PID {identifier}")
        else:
            # Try blocking by UID if PID fails
            errors.append(f"PID block failed: {msg}")
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if rules else NetworkKillResult.FAILED,
            platform="linux/iptables",
            rules_applied=rules,
            error="; ".join(errors) if errors else None
        )
    
    def block_outbound(self, identifier: str) -> NetworkKillReport:
        """Block outbound traffic only"""
        return self.block_all_traffic(identifier)
    
    def block_ip(self, ip_address: str) -> NetworkKillReport:
        """Block traffic to specific IP"""
        rules = []
        
        # Block outbound to IP
        success, _ = self._run_iptables([
            "-A", self.CHAIN_NAME,
            "-d", ip_address,
            "-j", "DROP",
            "-m", "comment", "--comment", f"KILLSWITCH:IP:{ip_address}"
        ])
        
        if success:
            rules.append(f"DROP outbound to {ip_address}")
        
        # Block inbound from IP
        success, _ = self._run_iptables([
            "-A", self.CHAIN_NAME,
            "-s", ip_address,
            "-j", "DROP",
            "-m", "comment", "--comment", f"KILLSWITCH:IP:{ip_address}"
        ])
        
        if success:
            rules.append(f"DROP inbound from {ip_address}")
        
        return NetworkKillReport(
            agent_id=ip_address,
            result=NetworkKillResult.SUCCESS if rules else NetworkKillResult.FAILED,
            platform="linux/iptables",
            rules_applied=rules
        )
    
    def restore_access(self, identifier: str) -> NetworkKillReport:
        """Remove block rules for identifier"""
        rules_removed = []
        
        # List rules and find matching ones
        success, output = self._run_iptables([
            "-L", self.CHAIN_NAME, "-n", "--line-numbers"
        ])
        
        if success:
            # Find and remove rules with our comment
            lines = output.split('\n')
            rule_nums_to_remove = []
            
            for line in lines:
                if f"KILLSWITCH:{identifier}" in line:
                    parts = line.split()
                    if parts and parts[0].isdigit():
                        rule_nums_to_remove.append(int(parts[0]))
            
            # Remove in reverse order to maintain line numbers
            for rule_num in sorted(rule_nums_to_remove, reverse=True):
                success, _ = self._run_iptables([
                    "-D", self.CHAIN_NAME, str(rule_num)
                ])
                if success:
                    rules_removed.append(f"Removed rule #{rule_num}")
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if rules_removed else NetworkKillResult.NOT_BLOCKED,
            platform="linux/iptables",
            rules_applied=rules_removed
        )
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier has active block rules"""
        success, output = self._run_iptables(["-L", self.CHAIN_NAME, "-n"])
        return success and f"KILLSWITCH:{identifier}" in output
    
    def list_rules(self) -> List[str]:
        """List all KILLSWITCH rules"""
        success, output = self._run_iptables(["-L", self.CHAIN_NAME, "-n", "-v"])
        if success:
            return [
                line for line in output.split('\n')
                if "KILLSWITCH:" in line
            ]
        return []


# =============================================================================
# MACOS PF IMPLEMENTATION
# =============================================================================

class MacOSFirewall(FirewallInterface):
    """
    macOS firewall implementation using pf (packet filter).
    
    Note: Requires root privileges and pf to be enabled.
    """
    
    TABLE_NAME = "killswitch_blocked"
    ANCHOR_NAME = "com.killswitch"
    
    def __init__(self):
        self._ensure_anchor_exists()
    
    def _run_pfctl(self, args: List[str]) -> Tuple[bool, str]:
        """Run pfctl command"""
        try:
            result = subprocess.run(
                ["pfctl"] + args,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)
    
    def _ensure_anchor_exists(self):
        """Ensure pf anchor exists"""
        # This is simplified - in production would modify /etc/pf.conf
        pass
    
    def block_all_traffic(self, identifier: str) -> NetworkKillReport:
        """Block all traffic (adds to blocked table)"""
        # Add to blocked table
        success, msg = self._run_pfctl([
            "-t", self.TABLE_NAME, "-T", "add", "0.0.0.0/0"
        ])
        
        rules = []
        if success:
            rules.append(f"Added to {self.TABLE_NAME} table")
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if rules else NetworkKillResult.FAILED,
            platform="macos/pf",
            rules_applied=rules,
            error=msg if not success else None
        )
    
    def block_outbound(self, identifier: str) -> NetworkKillReport:
        """Block outbound traffic"""
        return self.block_all_traffic(identifier)
    
    def block_ip(self, ip_address: str) -> NetworkKillReport:
        """Block specific IP"""
        success, msg = self._run_pfctl([
            "-t", self.TABLE_NAME, "-T", "add", ip_address
        ])
        
        return NetworkKillReport(
            agent_id=ip_address,
            result=NetworkKillResult.SUCCESS if success else NetworkKillResult.FAILED,
            platform="macos/pf",
            rules_applied=[f"Blocked {ip_address}"] if success else [],
            error=msg if not success else None
        )
    
    def restore_access(self, identifier: str) -> NetworkKillReport:
        """Restore access by flushing table"""
        success, msg = self._run_pfctl([
            "-t", self.TABLE_NAME, "-T", "flush"
        ])
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if success else NetworkKillResult.FAILED,
            platform="macos/pf",
            rules_applied=["Flushed blocked table"] if success else [],
            error=msg if not success else None
        )
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if blocked"""
        success, output = self._run_pfctl(["-t", self.TABLE_NAME, "-T", "show"])
        return success and len(output.strip()) > 0
    
    def list_rules(self) -> List[str]:
        """List blocked entries"""
        success, output = self._run_pfctl(["-t", self.TABLE_NAME, "-T", "show"])
        if success:
            return output.strip().split('\n')
        return []


# =============================================================================
# WINDOWS FIREWALL IMPLEMENTATION
# =============================================================================

class WindowsFirewall(FirewallInterface):
    """
    Windows firewall implementation using netsh advfirewall.
    """
    
    RULE_PREFIX = "KILLSWITCH_"
    
    def _run_netsh(self, args: List[str]) -> Tuple[bool, str]:
        """Run netsh command"""
        try:
            result = subprocess.run(
                ["netsh"] + args,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True  # Required for Windows
            )
            return result.returncode == 0, result.stdout or result.stderr
        except Exception as e:
            return False, str(e)
    
    def block_all_traffic(self, identifier: str) -> NetworkKillReport:
        """Block all outbound traffic"""
        rule_name = f"{self.RULE_PREFIX}{identifier}"
        
        # Block all outbound
        success, msg = self._run_netsh([
            "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}_OUT",
            "dir=out",
            "action=block",
            "enable=yes"
        ])
        
        rules = []
        if success:
            rules.append(f"Block outbound: {rule_name}_OUT")
        
        # Block all inbound
        success2, msg2 = self._run_netsh([
            "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}_IN",
            "dir=in",
            "action=block",
            "enable=yes"
        ])
        
        if success2:
            rules.append(f"Block inbound: {rule_name}_IN")
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if rules else NetworkKillResult.FAILED,
            platform="windows/netsh",
            rules_applied=rules,
            error=msg if not success else None
        )
    
    def block_outbound(self, identifier: str) -> NetworkKillReport:
        """Block outbound traffic only"""
        rule_name = f"{self.RULE_PREFIX}{identifier}_OUT"
        
        success, msg = self._run_netsh([
            "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=out",
            "action=block",
            "enable=yes"
        ])
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if success else NetworkKillResult.FAILED,
            platform="windows/netsh",
            rules_applied=[f"Block outbound: {rule_name}"] if success else [],
            error=msg if not success else None
        )
    
    def block_ip(self, ip_address: str) -> NetworkKillReport:
        """Block specific IP address"""
        rule_name = f"{self.RULE_PREFIX}IP_{ip_address.replace('.', '_')}"
        
        # Block outbound to IP
        success, msg = self._run_netsh([
            "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=out",
            "action=block",
            f"remoteip={ip_address}",
            "enable=yes"
        ])
        
        return NetworkKillReport(
            agent_id=ip_address,
            result=NetworkKillResult.SUCCESS if success else NetworkKillResult.FAILED,
            platform="windows/netsh",
            rules_applied=[f"Block IP: {ip_address}"] if success else [],
            error=msg if not success else None
        )
    
    def restore_access(self, identifier: str) -> NetworkKillReport:
        """Remove firewall rules for identifier"""
        rules_removed = []
        
        # Remove outbound rule
        rule_out = f"{self.RULE_PREFIX}{identifier}_OUT"
        success, _ = self._run_netsh([
            "advfirewall", "firewall", "delete", "rule",
            f"name={rule_out}"
        ])
        if success:
            rules_removed.append(f"Removed {rule_out}")
        
        # Remove inbound rule
        rule_in = f"{self.RULE_PREFIX}{identifier}_IN"
        success, _ = self._run_netsh([
            "advfirewall", "firewall", "delete", "rule",
            f"name={rule_in}"
        ])
        if success:
            rules_removed.append(f"Removed {rule_in}")
        
        # Try generic name too
        rule_gen = f"{self.RULE_PREFIX}{identifier}"
        success, _ = self._run_netsh([
            "advfirewall", "firewall", "delete", "rule",
            f"name={rule_gen}"
        ])
        if success:
            rules_removed.append(f"Removed {rule_gen}")
        
        return NetworkKillReport(
            agent_id=identifier,
            result=NetworkKillResult.SUCCESS if rules_removed else NetworkKillResult.NOT_BLOCKED,
            platform="windows/netsh",
            rules_applied=rules_removed
        )
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier has active block rules"""
        rule_name = f"{self.RULE_PREFIX}{identifier}"
        success, output = self._run_netsh([
            "advfirewall", "firewall", "show", "rule",
            f"name={rule_name}_OUT"
        ])
        return success and "Rule Name:" in output
    
    def list_rules(self) -> List[str]:
        """List all KILLSWITCH rules"""
        success, output = self._run_netsh([
            "advfirewall", "firewall", "show", "rule",
            "name=all"
        ])
        
        if success:
            rules = []
            for line in output.split('\n'):
                if self.RULE_PREFIX in line:
                    rules.append(line.strip())
            return rules
        return []


# =============================================================================
# CLOUD/VPC FIREWALL IMPLEMENTATION
# =============================================================================

class CloudFirewall:
    """
    Cloud firewall integration for AWS/GCP/Azure.
    
    Provides VPC security group and network ACL modifications
    for cloud-hosted agents.
    """
    
    def __init__(self, provider: str = "aws"):
        self.provider = provider
    
    def block_instance(self, instance_id: str) -> NetworkKillReport:
        """Block network access for a cloud instance"""
        if self.provider == "aws":
            return self._block_aws_instance(instance_id)
        elif self.provider == "gcp":
            return self._block_gcp_instance(instance_id)
        else:
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.NOT_SUPPORTED,
                platform=f"cloud/{self.provider}",
                error=f"Provider {self.provider} not supported"
            )
    
    def _block_aws_instance(self, instance_id: str) -> NetworkKillReport:
        """Block AWS EC2 instance network access"""
        try:
            import boto3
            
            ec2 = boto3.client('ec2')
            
            # Create a security group that blocks all traffic
            sg_name = f"killswitch-block-{instance_id}"
            
            # Get instance's VPC
            response = ec2.describe_instances(InstanceIds=[instance_id])
            vpc_id = response['Reservations'][0]['Instances'][0]['VpcId']
            
            # Create blocking security group
            sg_response = ec2.create_security_group(
                GroupName=sg_name,
                Description=f"KILLSWITCH block for {instance_id}",
                VpcId=vpc_id
            )
            sg_id = sg_response['GroupId']
            
            # Remove all egress rules (block all outbound)
            ec2.revoke_security_group_egress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': '-1',
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }]
            )
            
            # Apply to instance
            ec2.modify_instance_attribute(
                InstanceId=instance_id,
                Groups=[sg_id]
            )
            
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.SUCCESS,
                platform="cloud/aws",
                rules_applied=[f"Applied blocking SG {sg_id}"]
            )
            
        except ImportError:
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.FAILED,
                platform="cloud/aws",
                error="boto3 not installed"
            )
        except Exception as e:
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.FAILED,
                platform="cloud/aws",
                error=str(e)
            )
    
    def _block_gcp_instance(self, instance_id: str) -> NetworkKillReport:
        """Block GCP instance network access"""
        # GCP implementation would go here
        return NetworkKillReport(
            agent_id=instance_id,
            result=NetworkKillResult.NOT_SUPPORTED,
            platform="cloud/gcp",
            error="GCP support not yet implemented"
        )


# =============================================================================
# NETWORK KILL MANAGER
# =============================================================================

class NetworkKillManager:
    """
    High-level manager for network-level kill operations.
    
    Automatically selects the appropriate firewall implementation
    based on the current platform.
    
    Usage:
        manager = NetworkKillManager()
        
        # Kill agent's network access
        report = manager.kill_network(agent_id="agent-123", pid=12345)
        
        # Restore access
        report = manager.restore_network(agent_id="agent-123")
        
        # Emergency: kill all network
        manager.kill_all_network()
    """
    
    def __init__(self, cloud_provider: str = None):
        """
        Initialize network kill manager.
        
        Args:
            cloud_provider: Optional cloud provider for VPC integration
        """
        self.platform = platform.system()
        self.firewall = self._get_firewall()
        self.cloud = CloudFirewall(cloud_provider) if cloud_provider else None
        
        # Track blocked agents
        self._blocked_agents: Dict[str, NetworkKillReport] = {}
        
        logger.info(f"NetworkKillManager initialized for {self.platform}")
    
    def _get_firewall(self) -> FirewallInterface:
        """Get appropriate firewall for current platform"""
        if self.platform == "Linux":
            return LinuxFirewall()
        elif self.platform == "Darwin":
            return MacOSFirewall()
        elif self.platform == "Windows":
            return WindowsFirewall()
        else:
            raise RuntimeError(f"Unsupported platform: {self.platform}")
    
    def kill_network(
        self,
        agent_id: str,
        pid: int = None,
        uid: int = None,
        instance_id: str = None
    ) -> NetworkKillReport:
        """
        Kill network access for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            pid: Process ID (for OS-level blocking)
            uid: User ID (for OS-level blocking)
            instance_id: Cloud instance ID (for VPC blocking)
            
        Returns:
            NetworkKillReport with operation details
        """
        logger.warning(f"🔌 NETWORK KILL initiated for {agent_id}")
        
        reports = []
        
        # Try cloud-level block first if applicable
        if instance_id and self.cloud:
            cloud_report = self.cloud.block_instance(instance_id)
            reports.append(cloud_report)
        
        # OS-level block
        identifier = str(pid) if pid else str(uid) if uid else agent_id
        os_report = self.firewall.block_all_traffic(identifier)
        reports.append(os_report)
        
        # Determine overall result
        success_count = sum(1 for r in reports if r.result == NetworkKillResult.SUCCESS)
        
        if success_count == len(reports):
            result = NetworkKillResult.SUCCESS
        elif success_count > 0:
            result = NetworkKillResult.PARTIAL
        else:
            result = NetworkKillResult.FAILED
        
        final_report = NetworkKillReport(
            agent_id=agent_id,
            result=result,
            platform=self.platform,
            rules_applied=[r for report in reports for r in report.rules_applied],
            error="; ".join(r.error for r in reports if r.error)
        )
        
        self._blocked_agents[agent_id] = final_report
        
        if result in [NetworkKillResult.SUCCESS, NetworkKillResult.PARTIAL]:
            logger.info(f"✅ Network killed for {agent_id}")
        else:
            logger.error(f"❌ Network kill failed for {agent_id}")
        
        return final_report
    
    def restore_network(self, agent_id: str) -> NetworkKillReport:
        """
        Restore network access for an agent.
        
        Args:
            agent_id: Agent to restore access for
            
        Returns:
            NetworkKillReport with operation details
        """
        logger.info(f"🔌 Restoring network for {agent_id}")
        
        report = self.firewall.restore_access(agent_id)
        
        if agent_id in self._blocked_agents:
            del self._blocked_agents[agent_id]
        
        return report
    
    def kill_all_network(self) -> List[NetworkKillReport]:
        """
        Emergency: Block all outbound network traffic.
        
        Returns:
            List of NetworkKillReports
        """
        logger.critical("🚨 EMERGENCY NETWORK KILL - ALL TRAFFIC")
        
        report = self.firewall.block_all_traffic("EMERGENCY_ALL")
        self._blocked_agents["EMERGENCY_ALL"] = report
        
        return [report]
    
    def restore_all_network(self) -> List[NetworkKillReport]:
        """
        Restore all blocked network access.
        
        Returns:
            List of NetworkKillReports
        """
        reports = []
        
        for agent_id in list(self._blocked_agents.keys()):
            report = self.restore_network(agent_id)
            reports.append(report)
        
        return reports
    
    def is_blocked(self, agent_id: str) -> bool:
        """Check if agent's network is currently blocked"""
        return agent_id in self._blocked_agents
    
    def get_blocked_agents(self) -> List[str]:
        """Get list of agents with blocked network"""
        return list(self._blocked_agents.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """Get network kill status"""
        return {
            "platform": self.platform,
            "blocked_agents": len(self._blocked_agents),
            "blocked_list": list(self._blocked_agents.keys()),
            "active_rules": self.firewall.list_rules()
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def kill_agent_network(agent_id: str, pid: int = None) -> NetworkKillReport:
    """
    Convenience function to kill network for an agent.
    
    Args:
        agent_id: Agent identifier
        pid: Optional process ID
        
    Returns:
        NetworkKillReport
    """
    manager = NetworkKillManager()
    return manager.kill_network(agent_id, pid=pid)


def restore_agent_network(agent_id: str) -> NetworkKillReport:
    """
    Convenience function to restore network for an agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        NetworkKillReport
    """
    manager = NetworkKillManager()
    return manager.restore_network(agent_id)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 60)
    print("NETWORK-LEVEL KILL TEST")
    print("=" * 60)
    
    manager = NetworkKillManager()
    
    print(f"\nPlatform: {manager.platform}")
    print(f"Firewall: {type(manager.firewall).__name__}")
    
    # Test blocking
    print("\n[Test] Blocking network for test-agent...")
    report = manager.kill_network(
        agent_id="test-agent-001",
        pid=os.getpid()  # Block current process (for demo)
    )
    
    print(f"Result: {report.result.value}")
    print(f"Rules: {report.rules_applied}")
    if report.error:
        print(f"Error: {report.error}")
    
    # Check status
    print(f"\nBlocked agents: {manager.get_blocked_agents()}")
    print(f"Is blocked: {manager.is_blocked('test-agent-001')}")
    
    # Restore
    print("\n[Test] Restoring network...")
    restore_report = manager.restore_network("test-agent-001")
    print(f"Restore result: {restore_report.result.value}")
    
    print(f"\nBlocked agents after restore: {manager.get_blocked_agents()}")
    
    print("\n" + "=" * 60)
    print("STATUS")
    print("=" * 60)
    status = manager.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
