"""
SPIFFE/SPIRE Workload API Integration for Runtime Fence.

Provides agent identity verification using SPIFFE IDs and X.509-SVIDs
fetched from a local SPIRE Agent via the Workload API.

Requires: pip install runtime-fence[spiffe]
  Which installs: py-spiffe (the official SPIFFE Python library)
"""

import os
import logging
import threading
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Optional SPIFFE library
try:
    from pyspiffe.workloadapi import WorkloadApiClient
    SPIFFE_AVAILABLE = True
except ImportError:
    SPIFFE_AVAILABLE = False


@dataclass
class SpiffeConfig:
    """Configuration for SPIFFE/SPIRE integration."""
    # e.g., "unix:///tmp/spire-agent/public/api.sock"
    workload_api_addr: str = ""
    trust_domain: str = "runtime-fence.local"
    expected_spiffe_id_prefix: str = "spiffe://runtime-fence.local/agent/"
    svid_refresh_interval: int = 300  # Refresh SVID every 5 minutes
    enabled: bool = False


class SpiffeIdentityManager:
    """Manages agent identity via SPIFFE/SPIRE Workload API."""
    
    def __init__(self, config: SpiffeConfig = None):
        self.config = config or SpiffeConfig()
        self._client: Optional[object] = None
        self._current_svid: Optional[object] = None
        self._lock = threading.Lock()
        
        if not self.config.enabled:
            logger.info("SPIFFE integration disabled")
            return
        
        if not SPIFFE_AVAILABLE:
            logger.warning(
                "SPIFFE integration enabled but py-spiffe not installed. "
                "Install with: pip install runtime-fence[spiffe]"
            )
            return
        
        # Auto-detect workload API address
        if not self.config.workload_api_addr:
            self.config.workload_api_addr = os.environ.get(
                'SPIFFE_ENDPOINT_SOCKET',
                'unix:///tmp/spire-agent/public/api.sock'
            )
        
        self._connect()
    
    def _connect(self):
        """Connect to SPIRE Agent Workload API."""
        try:
            self._client = WorkloadApiClient(self.config.workload_api_addr)
            logger.info(
                f"Connected to SPIRE Agent at {self.config.workload_api_addr}"
            )
            self._refresh_svid()
        except Exception as e:
            logger.error(f"Failed to connect to SPIRE Agent: {e}")
            self._client = None
    
    def _refresh_svid(self):
        """Fetch or refresh the current X.509-SVID."""
        if not self._client:
            return
        try:
            with self._lock:
                svid_response = self._client.fetch_x509_svid()
                self._current_svid = svid_response
                spiffe_id = svid_response.spiffe_id
                logger.info(f"SVID refreshed: {spiffe_id}")
        except Exception as e:
            logger.error(f"Failed to fetch SVID: {e}")
    
    @property
    def spiffe_id(self) -> Optional[str]:
        """Get the current SPIFFE ID."""
        if self._current_svid:
            return str(self._current_svid.spiffe_id)
        return None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid SVID."""
        return self._current_svid is not None
    
    def validate_peer_id(self, peer_spiffe_id: str) -> bool:
        """Validate a peer's SPIFFE ID against trust domain and expected prefix."""
        if not peer_spiffe_id:
            return False

        # Must be in our trust domain
        expected_prefix = f"spiffe://{self.config.trust_domain}/"
        if not peer_spiffe_id.startswith(expected_prefix):
            logger.warning(
                f"Peer SPIFFE ID {peer_spiffe_id} not in trust domain "
                f"{self.config.trust_domain}"
            )
            return False

        # Must match expected agent ID pattern
        if self.config.expected_spiffe_id_prefix:
            if not peer_spiffe_id.startswith(
                self.config.expected_spiffe_id_prefix
            ):
                logger.warning(
                    f"Peer SPIFFE ID {peer_spiffe_id} doesn't match prefix"
                )
                return False

        return True
    
    def get_agent_identity(self, agent_id: str) -> dict:
        """Get identity information for an agent."""
        return {
            "agent_id": agent_id,
            "spiffe_id": self.spiffe_id,
            "trust_domain": self.config.trust_domain,
            "authenticated": self.is_authenticated,
            "workload_api": self.config.workload_api_addr,
        }
    
    def create_agent_spiffe_id(self, agent_id: str) -> str:
        """Generate the expected SPIFFE ID for a given agent."""
        return f"spiffe://{self.config.trust_domain}/agent/{agent_id}"
    
    def close(self):
        """Close the workload API connection."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
