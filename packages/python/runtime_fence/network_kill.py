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
import atexit
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
        """Run iptables command with privilege handling."""
        if platform.system() != 'Linux':
            return False, (
                f"iptables not available on {platform.system()}. "
                "Use platform-specific firewall."
            )
        
        try:
            # Use iptables directly if root, sudo -n otherwise
            if os.geteuid() == 0:
                cmd = ['iptables'] + args
            else:
                cmd = ['sudo', '-n', 'iptables'] + args
            
            result = subprocess.run(
                cmd, capture_output=True, timeout=10, check=True, text=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            return False, (
                f"iptables failed: {error_msg}. "
                "Requires root or sudo NOPASSWD config for iptables."
            )
        except FileNotFoundError:
            return False, (
                "iptables not found. Install with: apt install iptables"
            )
        except subprocess.TimeoutExpired:
            return False, "iptables command timed out after 10 seconds"
        except Exception as e:
            return False, f"Unexpected error running iptables: {str(e)}"
    
    def _get_process_uid(self, pid: str) -> Optional[int]:
        """Get the UID of a process by PID."""
        try:
            import psutil
            proc = psutil.Process(int(pid))
            return proc.uids().real
        except (psutil.NoSuchProcess, ValueError, psutil.AccessDenied):
            return None
    
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
        """Block all traffic by UID owner.
        
        NOTE: --pid-owner was removed from xt_owner in Linux kernel 3.14+
        Using --uid-owner which works on all modern kernels (3.14+)
        """
        rules = []
        errors = []
        
        # Resolve PID to UID for iptables owner match
        uid = self._get_process_uid(identifier)
        if uid is None:
            # Fallback: try using identifier as UID directly
            try:
                uid = int(identifier)
            except ValueError:
                return NetworkKillReport(
                    agent_id=identifier,
                    result=NetworkKillResult.FAILED,
                    platform="linux/iptables",
                    rules_applied=[],
                    error=f"Could not resolve PID {identifier} to UID"
                )
        
        # Block outbound by UID owner
        success, msg = self._run_iptables([
            "-A", self.CHAIN_NAME,
            "-m", "owner", "--uid-owner", str(uid),
            "-j", "DROP",
            "-m", "comment", "--comment", f"KILLSWITCH:{identifier}"
        ])
        
        if success:
            rules.append(
                f"DROP outbound for UID {uid} (from PID {identifier})"
            )
        else:
            errors.append(f"UID block failed: {msg}")
        
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
    Uses per-user rules to block only specific user's traffic,
    not global blocking that affects the entire system.
    """
    
    TABLE_NAME = "killswitch_blocked"
    ANCHOR_PREFIX = "com.killswitch."
    
    def __init__(self):
        self._blocked_uids: Dict[str, int] = {}  # identifier -> uid
        self._ensure_pf_enabled()
    
    def _run_pfctl(self, args: List[str]) -> Tuple[bool, str]:
        """Run pfctl command."""
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
    
    def _ensure_pf_enabled(self):
        """Ensure pf is enabled."""
        self._run_pfctl(["-e"])
    
    def _get_process_uid(self, pid: str) -> Optional[int]:
        """Get the UID of a process by PID."""
        try:
            import psutil
            proc = psutil.Process(int(pid))
            return proc.uids().real
        except (psutil.NoSuchProcess, ValueError, psutil.AccessDenied):
            return None
    
    def _get_pf_rules_for_user(self, uid: int) -> str:
        """Generate per-user pf rules for macOS."""
        return f"""# Runtime Fence - Agent Network Kill (UID: {uid})
block drop out quick proto tcp from any to any user {uid}
block drop out quick proto udp from any to any user {uid}
"""
    
    def _get_anchor_name(self, uid: int) -> str:
        """Get anchor name for a specific UID."""
        return f"{self.ANCHOR_PREFIX}{uid}"
    
    def block_all_traffic(self, identifier: str) -> NetworkKillReport:
        """Block all traffic for a specific user/agent using per-user rules."""
        # Get the UID of the process being killed
        uid = self._get_process_uid(identifier)
        if uid is None:
            # Fallback: try using identifier as UID directly
            try:
                uid = int(identifier)
            except ValueError:
                return NetworkKillReport(
                    agent_id=identifier,
                    result=NetworkKillResult.FAILED,
                    platform="macos/pf",
                    rules_applied=[],
                    error=f"Could not resolve PID {identifier} to UID"
                )
        
        # Store the UID for this identifier
        self._blocked_uids[identifier] = uid
        
        # Generate per-user pf rules
        rules_content = self._get_pf_rules_for_user(uid)
        anchor_name = self._get_anchor_name(uid)
        
        # Write rules to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.conf', delete=False
        ) as f:
            f.write(rules_content)
            rules_file = f.name
        
        try:
            # Load rules into a named anchor
            success, msg = self._run_pfctl([
                "-a", anchor_name, "-f", rules_file
            ])
            
            rules = []
            if success:
                rules.append(
                    f"Blocked UID {uid} (from PID {identifier}) "
                    f"via anchor {anchor_name}"
                )
                logger.info(
                    f"Applied per-user pf rules for UID {uid} "
                    f"in anchor {anchor_name}"
                )
            else:
                # Fallback to table-based blocking for IP
                success, msg = self._run_pfctl([
                    "-t", self.TABLE_NAME, "-T", "add", "0.0.0.0/0"
                ])
                if success:
                    rules.append(
                        f"FALLBACK: Added 0.0.0.0/0 to {self.TABLE_NAME} table"
                    )
                    logger.warning(
                        f"Fallback to global blocking for {identifier}"
                    )
            
            result = (
                NetworkKillResult.SUCCESS if rules else NetworkKillResult.FAILED
            )
            return NetworkKillReport(
                agent_id=identifier,
                result=result,
                platform="macos/pf",
                rules_applied=rules,
                error=msg if not success else None
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(rules_file)
            except OSError:
                pass
    
    def block_outbound(self, identifier: str) -> NetworkKillReport:
        """Block outbound traffic."""
        return self.block_all_traffic(identifier)
    
    def block_ip(self, ip_address: str) -> NetworkKillReport:
        """Block specific IP."""
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
        """Restore access by removing per-user anchor rules."""
        rules_removed = []
        
        # Check if we have a UID for this identifier
        if identifier in self._blocked_uids:
            uid = self._blocked_uids[identifier]
            anchor_name = self._get_anchor_name(uid)
            
            # Remove the anchor rules
            success, msg = self._run_pfctl([
                "-a", anchor_name, "-F", "all"
            ])
            
            if success:
                rules_removed.append(
                    f"Removed anchor {anchor_name} for UID {uid}"
                )
                logger.info(
                    f"Removed per-user pf rules for UID {uid}"
                )
            
            # Clean up
            del self._blocked_uids[identifier]
        
        # Also try flushing table as fallback cleanup
        success, _ = self._run_pfctl([
            "-t", self.TABLE_NAME, "-T", "flush"
        ])
        if success:
            rules_removed.append("Flushed blocked table")
        
        result = (
            NetworkKillResult.SUCCESS
            if rules_removed else NetworkKillResult.NOT_BLOCKED
        )
        return NetworkKillReport(
            agent_id=identifier,
            result=result,
            platform="macos/pf",
            rules_applied=rules_removed
        )
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked."""
        if identifier in self._blocked_uids:
            uid = self._blocked_uids[identifier]
            anchor_name = self._get_anchor_name(uid)
            success, output = self._run_pfctl([
                "-a", anchor_name, "-s", "rules"
            ])
            return success and len(output.strip()) > 0
        return False
    
    def list_rules(self) -> List[str]:
        """List blocked entries."""
        rules = []
        # List all killswitch anchors
        success, output = self._run_pfctl(["-s", "Anchors"])
        if success:
            for line in output.strip().split('\n'):
                if self.ANCHOR_PREFIX in line:
                    rules.append(line.strip())
        # Also list table entries
        success, output = self._run_pfctl([
            "-t", self.TABLE_NAME, "-T", "show"
        ])
        if success and output.strip():
            rules.extend(output.strip().split('\n'))
        return rules


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
        
        result = (
            NetworkKillResult.SUCCESS if rules else NetworkKillResult.FAILED
        )
        return NetworkKillReport(
            agent_id=identifier,
            result=result,
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
        
        result = (
            NetworkKillResult.SUCCESS if success else NetworkKillResult.FAILED
        )
        return NetworkKillReport(
            agent_id=identifier,
            result=result,
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
        
        result = (
            NetworkKillResult.SUCCESS if success else NetworkKillResult.FAILED
        )
        return NetworkKillReport(
            agent_id=ip_address,
            result=result,
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
        
        result = (
            NetworkKillResult.SUCCESS
            if rules_removed else NetworkKillResult.NOT_BLOCKED
        )
        return NetworkKillReport(
            agent_id=identifier,
            result=result,
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
        # Store original security groups for restoration
        self._original_sgs: Dict[str, List[str]] = {}
    
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
        """Block AWS EC2 instance network access."""
        try:
            import boto3
            
            ec2 = boto3.client('ec2')
            
            # Get instance details and VPC
            response = ec2.describe_instances(InstanceIds=[instance_id])
            instance_data = response['Reservations'][0]['Instances'][0]
            vpc_id = instance_data['VpcId']
            
            # Save original security groups for restoration
            original_sgs = [
                sg['GroupId'] for sg in instance_data['SecurityGroups']
            ]
            self._original_sgs[instance_id] = original_sgs
            logger.info(
                f"Saved original SGs for {instance_id}: {original_sgs}"
            )
            
            # Create a security group that blocks all traffic
            sg_name = f"killswitch-block-{instance_id}"
            
            try:
                # Try to create the blocking security group
                sg_response = ec2.create_security_group(
                    GroupName=sg_name,
                    Description=f"KILLSWITCH block for {instance_id}",
                    VpcId=vpc_id
                )
                sg_id = sg_response['GroupId']
            except Exception as e:
                # SG may already exist, find it
                if 'InvalidGroup.Duplicate' in str(e):
                    desc = ec2.describe_security_groups(
                        GroupNames=[sg_name]
                    )
                    sg_id = desc['SecurityGroups'][0]['GroupId']
                else:
                    raise
            
            # Remove all egress rules (block all outbound)
            try:
                ec2.revoke_security_group_egress(
                    GroupId=sg_id,
                    IpPermissions=[{
                        'IpProtocol': '-1',
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }]
                )
            except Exception:
                pass  # Egress rules may already be revoked
            
            # Replace ALL security groups with only the blocking SG
            ec2.modify_instance_attribute(
                InstanceId=instance_id,
                Groups=[sg_id]
            )
            logger.info(
                f"Replaced SGs {original_sgs} with blocking SG {sg_id}"
            )
            
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.SUCCESS,
                platform="cloud/aws",
                rules_applied=[
                    f"Replaced {original_sgs} with blocking SG {sg_id}"
                ]
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
        """Block GCP instance network access."""
        # GCP implementation would go here
        return NetworkKillReport(
            agent_id=instance_id,
            result=NetworkKillResult.NOT_SUPPORTED,
            platform="cloud/gcp",
            error="GCP support not yet implemented"
        )
    
    def restore_instance(self, instance_id: str) -> NetworkKillReport:
        """Restore network access for a cloud instance."""
        if self.provider == "aws":
            return self._restore_aws_instance(instance_id)
        elif self.provider == "gcp":
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.NOT_SUPPORTED,
                platform="cloud/gcp",
                error="GCP restore not yet implemented"
            )
        else:
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.NOT_SUPPORTED,
                platform=f"cloud/{self.provider}",
                error=f"Provider {self.provider} not supported"
            )
    
    def _restore_aws_instance(self, instance_id: str) -> NetworkKillReport:
        """Restore AWS EC2 instance network access."""
        try:
            import boto3
            
            ec2 = boto3.client('ec2')
            
            # Check if we have original security groups saved
            if instance_id not in self._original_sgs:
                return NetworkKillReport(
                    agent_id=instance_id,
                    result=NetworkKillResult.FAILED,
                    platform="cloud/aws",
                    error="No original security groups saved for this instance"
                )
            
            original_sgs = self._original_sgs[instance_id]
            
            # Restore original security groups
            ec2.modify_instance_attribute(
                InstanceId=instance_id,
                Groups=original_sgs
            )
            logger.info(
                f"Restored original SGs {original_sgs} for {instance_id}"
            )
            
            # Clean up the blocking security group
            sg_name = f"killswitch-block-{instance_id}"
            try:
                desc = ec2.describe_security_groups(GroupNames=[sg_name])
                sg_id = desc['SecurityGroups'][0]['GroupId']
                ec2.delete_security_group(GroupId=sg_id)
                logger.info(f"Deleted blocking SG {sg_id}")
            except Exception as e:
                logger.warning(f"Could not delete blocking SG: {e}")
            
            # Remove from saved state
            del self._original_sgs[instance_id]
            
            return NetworkKillReport(
                agent_id=instance_id,
                result=NetworkKillResult.SUCCESS,
                platform="cloud/aws",
                rules_applied=[
                    f"Restored original SGs: {original_sgs}"
                ]
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
        self._has_net_capabilities = True  # Assume capable until checked
        self.firewall = self._get_firewall()
        self.cloud = CloudFirewall(cloud_provider) if cloud_provider else None
    
        # Track blocked agents
        self._blocked_agents: Dict[str, NetworkKillReport] = {}
    
        # Check capabilities before registering cleanup
        self._check_capabilities()
    
        # Register cleanup on process exit
        atexit.register(self._cleanup_on_exit)
    
        logger.info(f"NetworkKillManager initialized for {self.platform}")
    
    def _check_capabilities(self):
        """Check if we have network administration capabilities."""
        system = platform.system()
    
        if system == "Linux":
            if os.geteuid() != 0:
                # Check for NET_ADMIN capability
                try:
                    with open(f'/proc/{os.getpid()}/status', 'r') as f:
                        for line in f:
                            if line.startswith('CapEff:'):
                                cap_hex = int(line.split(':')[1].strip(), 16)
                                has_net_admin = bool(cap_hex & (1 << 12))
                                if not has_net_admin:
                                    logger.warning(
                                        "No root or NET_ADMIN capability — "
                                        "network_kill.py will use "
                                        "application-level kill only. "
                                        "Run with: sudo setcap "
                                        "cap_net_admin+ep $(which python)"
                                    )
                                    self._has_net_capabilities = False
                                    return
                except Exception:
                    pass
                logger.warning(
                    "No root — network_kill.py will use app-level kill only"
                )
                self._has_net_capabilities = False
                return
    
        elif system == "Darwin":
            if os.geteuid() != 0:
                logger.warning(
                    "No root — macOS pf rules require sudo, "
                    "using app-level kill only"
                )
                self._has_net_capabilities = False
                return
    
        elif system == "Windows":
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                logger.warning(
                    "Not running as Administrator — "
                    "netsh rules unavailable"
                )
                self._has_net_capabilities = False
                return
    
        self._has_net_capabilities = True
    
    def _cleanup_on_exit(self):
        """Restore all network rules on process exit."""
        try:
            self.restore_all_network()
            logger.info("Network rules cleaned up on exit")
        except Exception as e:
            logger.error(f"Failed to clean up network rules on exit: {e}")
    
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
        
        # OS-level block (only if we have capabilities)
        identifier = str(pid) if pid else str(uid) if uid else agent_id
        if self._has_net_capabilities:
            os_report = self.firewall.block_all_traffic(identifier)
            reports.append(os_report)
        else:
            # No firewall capabilities - report as permission denied
            os_report = NetworkKillReport(
                agent_id=identifier,
                result=NetworkKillResult.PERMISSION_DENIED,
                platform=self.platform,
                rules_applied=[],
                error="No firewall capabilities - application-level kill only"
            )
            reports.append(os_report)
        
        # Determine overall result
        success_count = sum(
            1 for r in reports if r.result == NetworkKillResult.SUCCESS
        )
        
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
            rules_applied=[
                r for report in reports for r in report.rules_applied
            ],
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
