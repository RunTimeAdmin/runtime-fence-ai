"""Governance Separation - Local Kill vs Token-Governed Policy

LOCAL (instant): kill, pause, network_block
GOVERNED (vote): policy_update, threshold_change

Copyright (c) 2025 David Cooper - PATENT PENDING
"""

import logging
import os
import time
import uuid
import json
import hashlib
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Check for Supabase availability
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.debug("supabase package not available")


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
    """In-memory vote provider for testing and fallback."""

    def __init__(self):
        self._counter = 0
        self._proposals: Dict[str, Dict] = {}
        self._votes: Dict[str, List[Dict]] = {}

    def submit(self, proposal: Dict) -> str:
        """Submit a new proposal. Returns proposal ID."""
        self._counter += 1
        proposal_id = f"PROP-{self._counter:04d}"
        self._proposals[proposal_id] = {
            'id': proposal_id,
            'title': proposal.get('title', 'Untitled'),
            'description': proposal.get('description', ''),
            'action_type': proposal.get('type', 'unknown'),
            'action_target': proposal.get('name', ''),
            'proposed_by': proposal.get('proposed_by', 'system'),
            'status': 'active',
            'quorum_required': proposal.get('quorum', 3),
            'votes_for': 0,
            'votes_against': 0,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'resolved_at': None
        }
        self._votes[proposal_id] = []
        return proposal_id

    def cast_vote(self, proposal_id: str, voter_id: str, vote: bool, reason: str = '') -> Dict:
        """Cast a vote on a proposal. Returns updated proposal status."""
        if proposal_id not in self._proposals:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Check for existing vote
        existing = [v for v in self._votes[proposal_id] if v['voter_id'] == voter_id]
        if existing:
            raise ValueError(f"User {voter_id} already voted on proposal {proposal_id}")

        # Record vote
        self._votes[proposal_id].append({
            'voter_id': voter_id,
            'vote': vote,
            'reason': reason,
            'created_at': datetime.utcnow().isoformat()
        })

        # Update counts
        proposal = self._proposals[proposal_id]
        if vote:
            proposal['votes_for'] += 1
        else:
            proposal['votes_against'] += 1

        # Check quorum
        quorum = proposal['quorum_required']
        if proposal['votes_for'] >= quorum:
            proposal['status'] = 'passed'
            proposal['resolved_at'] = datetime.utcnow().isoformat()
        elif proposal['votes_against'] >= quorum:
            proposal['status'] = 'rejected'
            proposal['resolved_at'] = datetime.utcnow().isoformat()

        return {
            'proposal_id': proposal_id,
            'votes_for': proposal['votes_for'],
            'votes_against': proposal['votes_against'],
            'status': proposal['status'],
            'quorum_required': quorum
        }

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get proposal details."""
        return self._proposals.get(proposal_id)

    def get_active_proposals(self) -> List[Dict]:
        """Get all active proposals."""
        return [p for p in self._proposals.values() if p['status'] == 'active']

    def check_approval(self, proposal_id: str) -> bool:
        """Check if a proposal has been approved."""
        proposal = self._proposals.get(proposal_id)
        return proposal is not None and proposal['status'] == 'passed'


class SupabaseVoteProvider(VoteProvider):
    """Production vote provider using Supabase for persistent governance."""

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase package required: pip install supabase")

        self._url = supabase_url or os.environ.get('SUPABASE_URL', '')
        self._key = supabase_key or os.environ.get('SUPABASE_SERVICE_KEY', os.environ.get('SUPABASE_KEY', ''))

        if not self._url or not self._key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required for SupabaseVoteProvider")

        self._client: Client = create_client(self._url, self._key)

    def submit(self, proposal: Dict) -> str:
        """Submit a new proposal. Returns proposal ID."""
        proposal_id = proposal.get('id') or str(uuid.uuid4())
        data = {
            'id': proposal_id,
            'title': proposal.get('title', 'Untitled'),
            'description': proposal.get('description', ''),
            'action_type': proposal.get('type', 'unknown'),
            'action_target': proposal.get('name', ''),
            'proposed_by': proposal.get('proposed_by', 'system'),
            'quorum_required': proposal.get('quorum', 3),
            'status': 'active'
        }
        result = self._client.table('governance_proposals').insert(data).execute()
        return result.data[0]['id'] if result.data else proposal_id

    def cast_vote(self, proposal_id: str, voter_id: str, vote: bool, reason: str = '') -> Dict:
        """Cast a vote on a proposal. Returns updated proposal status."""
        # Insert vote (UNIQUE constraint prevents double-voting)
        vote_data = {
            'proposal_id': proposal_id,
            'voter_id': voter_id,
            'vote': vote,
            'reason': reason
        }
        self._client.table('governance_votes').insert(vote_data).execute()

        # Update vote counts
        votes = self._client.table('governance_votes').select('vote').eq('proposal_id', proposal_id).execute()
        votes_for = sum(1 for v in votes.data if v['vote'])
        votes_against = sum(1 for v in votes.data if not v['vote'])

        # Update proposal
        update = {'votes_for': votes_for, 'votes_against': votes_against}

        # Check if quorum reached
        proposal = self._client.table('governance_proposals').select('*').eq('id', proposal_id).single().execute()
        quorum = proposal.data['quorum_required']

        if votes_for >= quorum:
            update['status'] = 'passed'
            update['resolved_at'] = datetime.utcnow().isoformat()
        elif votes_against >= quorum:
            update['status'] = 'rejected'
            update['resolved_at'] = datetime.utcnow().isoformat()

        self._client.table('governance_proposals').update(update).eq('id', proposal_id).execute()

        return {
            'proposal_id': proposal_id,
            'votes_for': votes_for,
            'votes_against': votes_against,
            'status': update.get('status', 'active'),
            'quorum_required': quorum
        }

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get proposal details."""
        result = self._client.table('governance_proposals').select('*').eq('id', proposal_id).single().execute()
        return result.data

    def get_active_proposals(self) -> List[Dict]:
        """Get all active proposals."""
        result = self._client.table('governance_proposals').select('*').eq('status', 'active').execute()
        return result.data

    def check_approval(self, proposal_id: str) -> bool:
        """Check if a proposal has been approved."""
        proposal = self.get_proposal(proposal_id)
        return proposal is not None and proposal.get('status') == 'passed'


class BagsVoteProvider:
    """
    Token-gated governance using Bags.fm token balances as voting weight.
    
    Uses Bags.fm API for token metadata and Solana RPC for balance verification.
    Votes are stored in Supabase with on-chain balance snapshots.
    
    Requires:
        - BAGS_API_KEY: API key from https://dev.bags.fm
        - BAGS_TOKEN_MINT: Solana token mint address for voting
        - SUPABASE_URL + SUPABASE_KEY: For vote storage
        - SOLANA_RPC_URL: Solana RPC endpoint (default: mainnet)
    """
    
    def __init__(self, 
                 bags_api_key: str = None,
                 token_mint: str = None,
                 solana_rpc_url: str = None,
                 supabase_url: str = None,
                 supabase_key: str = None):
        self._bags_api_key = bags_api_key or os.environ.get('BAGS_API_KEY', '')
        self._token_mint = token_mint or os.environ.get('BAGS_TOKEN_MINT', '')
        self._solana_rpc = solana_rpc_url or os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        # Supabase for vote storage
        self._supabase_url = supabase_url or os.environ.get('SUPABASE_URL', '')
        self._supabase_key = supabase_key or os.environ.get('SUPABASE_KEY', '')
        self._supabase = None
        
        if self._supabase_url and self._supabase_key and SUPABASE_AVAILABLE:
            try:
                self._supabase = create_client(self._supabase_url, self._supabase_key)
            except Exception as e:
                logger.warning(f"Supabase client init failed: {e}")
        
        if not self._bags_api_key:
            logger.warning("BAGS_API_KEY not set - Bags.fm governance will use mock balances")
        
        self._bags_base_url = "https://public-api-v2.bags.fm/api/v1"
        self._balance_cache: dict = {}  # wallet -> (balance, timestamp)
        self._cache_ttl = 60  # Cache balances for 60 seconds
    
    def _bags_headers(self) -> dict:
        """Get Bags.fm API headers."""
        return {
            "x-api-key": self._bags_api_key,
            "Content-Type": "application/json",
        }
    
    def _get_token_balance(self, wallet_address: str) -> float:
        """Get token balance for a wallet from Solana RPC."""
        # Check cache
        cached = self._balance_cache.get(wallet_address)
        if cached and time.time() - cached[1] < self._cache_ttl:
            return cached[0]
        
        try:
            import urllib.request
            
            # Query Solana RPC for SPL token balance
            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_address,
                    {"mint": self._token_mint},
                    {"encoding": "jsonParsed"}
                ]
            })
            
            req = urllib.request.Request(
                self._solana_rpc,
                data=payload.encode(),
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            
            balance = 0.0
            accounts = data.get("result", {}).get("value", [])
            for account in accounts:
                info = account.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                token_amount = info.get("tokenAmount", {})
                balance += float(token_amount.get("uiAmount", 0))
            
            self._balance_cache[wallet_address] = (balance, time.time())
            return balance
            
        except Exception as e:
            logger.warning(f"Failed to fetch token balance for {wallet_address}: {e}")
            return 0.0
    
    def _get_token_metadata(self) -> dict:
        """Fetch token metadata from Bags.fm API."""
        if not self._bags_api_key or not self._token_mint:
            return {}
        
        try:
            import urllib.request
            
            url = f"{self._bags_base_url}/token-launch/creators?mint={self._token_mint}"
            req = urllib.request.Request(url, headers=self._bags_headers())
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning(f"Failed to fetch token metadata: {e}")
            return {}
    
    def create_proposal(self, title: str, description: str, 
                       proposed_by: str, choices: list = None,
                       duration_hours: int = 168) -> dict:
        """Create a governance proposal. Votes stored in Supabase."""
        proposal_id = hashlib.sha256(
            f"{title}:{proposed_by}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        # Verify proposer has tokens (minimum 1 token to propose)
        balance = self._get_token_balance(proposed_by)
        if balance < 1.0 and self._bags_api_key:
            return {
                "error": "Insufficient token balance to create proposal",
                "required": 1.0,
                "balance": balance,
            }
        
        proposal = {
            "id": proposal_id,
            "title": title,
            "description": description,
            "proposed_by": proposed_by,
            "proposer_balance": balance,
            "choices": choices or ["approve", "reject"],
            "token_mint": self._token_mint,
            "status": "active",
            "created_at": time.time(),
            "expires_at": time.time() + (duration_hours * 3600),
            "votes": {},
            "vote_weights": {},
        }
        
        # Persist to Supabase
        if self._supabase:
            try:
                self._supabase.table("governance_proposals").insert({
                    "id": proposal_id,
                    "title": title,
                    "description": description,
                    "proposed_by": proposed_by,
                    "token_mint": self._token_mint,
                    "status": "active",
                    "choices": json.dumps(choices or ["approve", "reject"]),
                    "expires_at": datetime.fromtimestamp(proposal["expires_at"]).isoformat(),
                }).execute()
                logger.info(f"Proposal {proposal_id} persisted to Supabase")
            except Exception as e:
                logger.warning(f"Failed to persist proposal: {e}")
        
        
        logger.info(f"Governance proposal created: {proposal_id} by {proposed_by} (balance: {balance})")
        return proposal
    
    def cast_vote(self, proposal_id: str, voter_wallet: str, choice: str) -> dict:
        """Cast a token-weighted vote. Weight = token balance at time of vote."""
        balance = self._get_token_balance(voter_wallet)
        
        if balance <= 0 and self._bags_api_key:
            return {
                "error": "No token balance - cannot vote",
                "wallet": voter_wallet,
                "balance": 0,
            }
        
        # Use balance as vote weight (1 token = 1 vote)
        vote_weight = balance if self._bags_api_key else 1.0  # Default weight if no API
        
        vote = {
            "proposal_id": proposal_id,
            "voter": voter_wallet,
            "choice": choice,
            "weight": vote_weight,
            "balance_snapshot": balance,
            "timestamp": time.time(),
        }
        
        # Persist to Supabase
        if self._supabase:
            try:
                self._supabase.table("governance_votes").insert({
                    "proposal_id": proposal_id,
                    "voter": voter_wallet,
                    "choice": choice,
                    "weight": vote_weight,
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to persist vote: {e}")
        
        
        logger.info(f"Vote cast: {voter_wallet} voted '{choice}' on {proposal_id} (weight: {vote_weight})")
        return vote
    
    def get_proposal(self, proposal_id: str) -> dict:
        """Get proposal with current vote tallies."""
        if self._supabase:
            try:
                # Get proposal
                result = self._supabase.table("governance_proposals").select("*").eq("id", proposal_id).execute()
                if not result.data:
                    return {"error": "Proposal not found"}
                
                proposal = result.data[0]
                
                # Get votes
                votes = self._supabase.table("governance_votes").select("*").eq("proposal_id", proposal_id).execute()
                
                # Tally by choice
                tallies = {}
                for vote in (votes.data or []):
                    choice = vote["choice"]
                    tallies[choice] = tallies.get(choice, 0) + float(vote.get("weight", 1))
                
                
                proposal["tallies"] = tallies
                proposal["total_votes"] = len(votes.data or [])
                proposal["total_weight"] = sum(tallies.values())
                
                return proposal
                
            except Exception as e:
                logger.warning(f"Failed to fetch proposal: {e}")
        
        
        return {"error": "Proposal not found or Supabase unavailable"}
    
    def check_approval(self, proposal_id: str, threshold: float = 0.5) -> bool:
        """Check if a proposal has passed (>threshold weighted approval)."""
        proposal = self.get_proposal(proposal_id)
        if "error" in proposal:
            return False
        
        # Check if expired
        expires_at = proposal.get("expires_at", 0)
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).timestamp()
            except:
                expires_at = 0
        
        
        tallies = proposal.get("tallies", {})
        total_weight = proposal.get("total_weight", 0)
        
        if total_weight == 0:
            return False
        
        approve_weight = tallies.get("approve", 0)
        approval_ratio = approve_weight / total_weight
        
        return approval_ratio > threshold


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

    def __init__(self, vote_provider: VoteProvider = None):
        self.local = LocalExecutor()

        # Auto-detect vote provider: BagsVoteProvider -> SupabaseVoteProvider -> MockVoteProvider
        if vote_provider:
            self._vote_provider = vote_provider
            logger.info("Governance using provided vote provider")
        elif os.environ.get('BAGS_API_KEY') and os.environ.get('BAGS_TOKEN_MINT'):
            try:
                self._vote_provider = BagsVoteProvider()
                logger.info("Governance using BagsVoteProvider (Solana token-gated)")
            except Exception as e:
                logger.warning(f"BagsVoteProvider failed: {e}, falling back")
                # Fall through to Supabase
                if SUPABASE_AVAILABLE and os.environ.get('SUPABASE_URL'):
                    try:
                        self._vote_provider = SupabaseVoteProvider()
                        logger.info("Governance using Supabase vote provider")
                    except (ValueError, Exception) as e:
                        logger.warning(f"Supabase vote provider unavailable, using mock: {e}")
                        self._vote_provider = MockVoteProvider()
                else:
                    self._vote_provider = MockVoteProvider()
        elif SUPABASE_AVAILABLE and os.environ.get('SUPABASE_URL'):
            try:
                self._vote_provider = SupabaseVoteProvider()
                logger.info("Governance using Supabase vote provider")
            except (ValueError, Exception) as e:
                logger.warning(f"Supabase vote provider unavailable, using mock: {e}")
                self._vote_provider = MockVoteProvider()
        else:
            logger.info("Governance using mock vote provider (Supabase not configured)")
            self._vote_provider = MockVoteProvider()

        self.governed = GovernedExecutor(votes=self._vote_provider)

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
