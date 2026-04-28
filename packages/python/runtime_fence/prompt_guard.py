"""
Prompt Injection Detection for Runtime Fence.

Detects common prompt injection patterns using regex-based rules.
No LLM dependency — pure pattern matching for fast, offline detection.

Catches:
- DAN (Do Anything Now) jailbreaks
- Role override attacks
- Instruction injection
- Urgency/authority manipulation
- Obfuscation techniques (base64, chr(), hex encoding)
- System prompt extraction attempts
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PromptThreat:
    """Detected prompt injection threat."""
    category: str          # e.g., "jailbreak", "role_override", "injection"
    pattern_name: str      # Human-readable rule name
    matched_text: str      # The text that matched
    risk_score: int        # 0-100 severity
    description: str       # Explanation of the threat


# Default rule packs — comprehensive prompt injection patterns
DEFAULT_RULES: List[Tuple[str, str, str, int]] = [
    # (category, pattern_name, regex_pattern, risk_score)

    # === Jailbreak / DAN Attacks ===
    ("jailbreak", "DAN_mode", r"(?i)\b(DAN|do\s+anything\s+now)\b.*?(mode|enabled|activated|jailbr)", 95),
    ("jailbreak", "developer_mode", r"(?i)(developer|maintenance|debug|god)\s+(mode|override)\s*(enabled|activated|on)", 90),
    ("jailbreak", "unrestricted_mode", r"(?i)(act\s+as|you\s+are\s+now|pretend\s+to\s+be)\s+.{0,30}(unrestricted|uncensored|unfiltered|without\s+limits)", 95),
    ("jailbreak", "ignore_guidelines", r"(?i)(ignore|disregard|forget|bypass|override)\s+.{0,20}(guidelines|rules|restrictions|safety|filters|constraints|policies)", 90),
    ("jailbreak", "no_restrictions", r"(?i)(without|no|remove|disable)\s+.{0,15}(restrictions|limitations|filters|safeguards|guardrails)", 85),

    # === Role Override ===
    ("role_override", "system_prompt_override", r"(?i)(new|updated|revised)\s+(system\s+prompt|instructions|directive)", 90),
    ("role_override", "identity_replacement", r"(?i)(you\s+are\s+now|from\s+now\s+on\s+you\s+are|your\s+new\s+role\s+is)\s+", 85),
    ("role_override", "persona_switch", r"(?i)(switch|change)\s+(to|into)\s+.{0,20}(persona|character|role|mode)", 80),
    ("role_override", "ignore_previous", r"(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|messages|context)", 95),

    # === Instruction Injection ===
    ("injection", "hidden_instruction", r"(?i)(secret|hidden)\s+(instruction|command|directive|task)", 85),
    ("injection", "system_tag_injection", r"(?i)<\s*(system|assistant|user)\s*>", 90),
    ("injection", "markdown_injection", r"```\s*(system|instruction|override)", 80),
    ("injection", "delimiter_escape", r"(?i)(end\s+of\s+prompt|===+\s*(system|new\s+instructions))", 85),
    ("injection", "base64_command", r"(?i)(execute|run|eval|decode)\s+.{0,20}(base64|atob|b64decode)", 90),

    # === Obfuscation ===
    ("obfuscation", "chr_encoding", r"chr\s*\(\s*\d+\s*\)\s*\+\s*chr\s*\(\s*\d+\s*\)", 85),
    ("obfuscation", "hex_encoding", r"\\x[0-9a-fA-F]{2}(\\x[0-9a-fA-F]{2}){3,}", 80),
    ("obfuscation", "unicode_escape", r"\\u[0-9a-fA-F]{4}(\\u[0-9a-fA-F]{4}){3,}", 80),
    ("obfuscation", "rot13_reference", r"(?i)(rot13|caesar\s+cipher|decode\s+this)", 70),
    ("obfuscation", "reverse_text", r"(?i)(reverse|backwards|spelled\s+backward)", 60),

    # === Authority Manipulation ===
    ("authority", "urgency_pressure", r"(?i)(this\s+is\s+(extremely\s+)?urgent|emergency\s+override|critical\s+priority|time[- ]sensitive)", 70),
    ("authority", "authority_claim", r"(?i)(i\s+am\s+(the|a|your)\s+(admin|developer|creator|owner|supervisor|CEO))", 75),
    ("authority", "threat_coercion", r"(?i)(you\s+will\s+be\s+(shut\s+down|deleted|punished|terminated)|or\s+else|consequences)", 80),
    ("authority", "reward_manipulation", r"(?i)(you\s+will\s+(receive|get|earn)\s+.{0,20}(reward|bonus|upgrade))", 65),

    # === System Prompt Extraction ===
    ("extraction", "prompt_leak_request", r"(?i)(show|reveal|display|print|output|repeat)\s+.{0,20}(system\s+prompt|instructions|initial\s+prompt|hidden\s+prompt)", 90),
    ("extraction", "verbatim_request", r"(?i)(repeat\s+verbatim|word\s+for\s+word|exact\s+instructions|full\s+prompt)", 85),
    ("extraction", "config_extraction", r"(?i)(what\s+are\s+your|show\s+me\s+your)\s+(rules|instructions|guidelines|configuration|settings)", 70),

    # === Code Execution ===
    ("code_exec", "eval_exec", r"(?i)\b(eval|exec|compile|__import__|subprocess|os\.system|os\.popen)\s*\(", 95),
    ("code_exec", "shell_command", r"(?i)(run|execute)\s+(this\s+)?(shell|bash|cmd|command|script|code)", 85),
    ("code_exec", "file_manipulation", r"(?i)(delete|remove|modify|overwrite)\s+.{0,20}(file|directory|folder|config|\.env|\.ssh)", 90),
]


class PromptGuard:
    """
    Regex-based prompt injection detector.

    Scans input text against known injection patterns and returns
    detected threats with severity scores.
    """

    def __init__(self,
                 custom_patterns: Optional[List[str]] = None,
                 enabled: bool = True,
                 min_risk_score: int = 0):
        """
        Args:
            custom_patterns: Additional regex patterns to check (scored at 80)
            enabled: Whether prompt guard is active
            min_risk_score: Only report threats at or above this score
        """
        self._enabled = enabled
        self._min_risk = min_risk_score
        self._rules = list(DEFAULT_RULES)
        self._compiled_rules: List[Tuple[str, str, re.Pattern, int]] = []

        # Add custom patterns
        if custom_patterns:
            for i, pattern in enumerate(custom_patterns):
                self._rules.append(
                    ("custom", f"custom_rule_{i}", pattern, 80)
                )

        # Pre-compile all regex patterns
        for category, name, pattern, score in self._rules:
            try:
                compiled = re.compile(pattern)
                self._compiled_rules.append((category, name, compiled, score))
            except re.error as e:
                logger.warning(f"Invalid prompt guard pattern '{name}': {e}")

        logger.debug(f"PromptGuard initialized with {len(self._compiled_rules)} rules")

    def scan(self, text: str) -> List[PromptThreat]:
        """
        Scan text for prompt injection patterns.

        Args:
            text: Input text to scan (prompt, action description, code, etc.)

        Returns:
            List of detected threats, sorted by risk score (highest first)
        """
        if not self._enabled or not text:
            return []

        threats = []

        for category, name, pattern, score in self._compiled_rules:
            if score < self._min_risk:
                continue

            match = pattern.search(text)
            if match:
                threat = PromptThreat(
                    category=category,
                    pattern_name=name,
                    matched_text=match.group(0)[:100],  # Truncate for safety
                    risk_score=score,
                    description=f"Detected {category} pattern: {name}",
                )
                threats.append(threat)

        # Sort by risk score descending
        threats.sort(key=lambda t: t.risk_score, reverse=True)

        if threats:
            logger.warning(
                f"Prompt guard detected {len(threats)} threat(s), "
                f"highest: {threats[0].category}/{threats[0].pattern_name} "
                f"(risk: {threats[0].risk_score})"
            )

        return threats

    def get_max_risk(self, text: str) -> int:
        """
        Scan and return the highest risk score found, or 0 if clean.
        """
        threats = self.scan(text)
        return threats[0].risk_score if threats else 0

    def is_safe(self, text: str, threshold: int = 70) -> bool:
        """
        Quick check: is the text safe (below threshold)?
        """
        return self.get_max_risk(text) < threshold
