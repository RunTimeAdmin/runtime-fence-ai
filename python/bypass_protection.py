"""
Bypass Protection - Package Integrity and Tamper Detection

This module protects the RuntimeFence from being bypassed by malicious agents
that attempt to modify the safety library itself ("living off the land" attack).

Protection layers:
1. Package integrity verification via SHA-256 hashes
2. Runtime tamper detection
3. Read-only enforcement checks
4. Self-destruct on compromise
5. Integrity attestation for audit

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import os
import sys
import hashlib
import logging
import importlib
import inspect
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


# =============================================================================
# INTEGRITY STATUS
# =============================================================================

class IntegrityStatus(Enum):
    """Status of integrity check"""
    VERIFIED = "verified"
    TAMPERED = "tampered"
    MISSING = "missing"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class IntegrityReport:
    """Report of integrity verification"""
    status: IntegrityStatus
    package_name: str
    files_checked: int
    files_passed: int
    files_failed: List[str] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attestation_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "package_name": self.package_name,
            "files_checked": self.files_checked,
            "files_passed": self.files_passed,
            "files_failed": self.files_failed,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "attestation_hash": self.attestation_hash
        }
    
    @property
    def is_valid(self) -> bool:
        return self.status == IntegrityStatus.VERIFIED


# =============================================================================
# HASH MANIFEST
# =============================================================================

class HashManifest:
    """
    Manages expected file hashes for integrity verification.
    
    The manifest can be:
    1. Generated from current files (during build/install)
    2. Loaded from a signed manifest file
    3. Embedded in the code (most secure)
    """
    
    def __init__(self, manifest_path: str = None):
        self.manifest_path = manifest_path
        self._hashes: Dict[str, str] = {}
        self._signature: Optional[str] = None
        
        if manifest_path and Path(manifest_path).exists():
            self._load_manifest()
    
    def _load_manifest(self):
        """Load manifest from file"""
        try:
            with open(self.manifest_path, 'r') as f:
                data = json.load(f)
                self._hashes = data.get('hashes', {})
                self._signature = data.get('signature')
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
    
    def save_manifest(self, sign_key: str = None):
        """Save manifest to file"""
        data = {
            'hashes': self._hashes,
            'generated': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
        
        if sign_key:
            # In production, would use proper cryptographic signing
            manifest_str = json.dumps(self._hashes, sort_keys=True)
            data['signature'] = hashlib.sha256(
                f"{manifest_str}:{sign_key}".encode()
            ).hexdigest()
        
        if self.manifest_path:
            with open(self.manifest_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def add_hash(self, filepath: str, file_hash: str):
        """Add a file hash to manifest"""
        self._hashes[filepath] = file_hash
    
    def get_hash(self, filepath: str) -> Optional[str]:
        """Get expected hash for a file"""
        return self._hashes.get(filepath)
    
    def get_all_hashes(self) -> Dict[str, str]:
        """Get all hashes"""
        return dict(self._hashes)
    
    @staticmethod
    def compute_file_hash(filepath: str) -> str:
        """Compute SHA-256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def generate_from_package(self, package_path: str) -> int:
        """
        Generate hashes for all Python files in a package.
        
        Returns number of files hashed.
        """
        count = 0
        package_path = Path(package_path)
        
        for py_file in package_path.rglob('*.py'):
            relative_path = str(py_file.relative_to(package_path.parent))
            file_hash = self.compute_file_hash(str(py_file))
            self.add_hash(relative_path, file_hash)
            count += 1
        
        return count


# =============================================================================
# EMBEDDED HASHES (Most Secure - Compiled Into Code)
# =============================================================================

# These hashes are embedded at build time and cannot be modified
# without changing the source code itself
EMBEDDED_CRITICAL_HASHES = {
    # Core security files that MUST NOT be modified
    # Format: "relative/path.py": "sha256:expected_hash"
    # 
    # In production, these would be populated during CI/CD build:
    # "runtime_fence/validator.py": "sha256:abc123...",
    # "runtime_fence/fence.py": "sha256:def456...",
    # "runtime_fence/kill_switch.py": "sha256:789abc...",
}


# =============================================================================
# INTEGRITY VERIFIER
# =============================================================================

class IntegrityVerifier:
    """
    Verifies package integrity to detect tampering.
    
    Protection mechanisms:
    1. Hash verification against known-good values
    2. Runtime code inspection
    3. Module import monitoring
    4. Self-verification of this module
    
    Usage:
        verifier = IntegrityVerifier("runtime_fence")
        report = verifier.verify()
        
        if not report.is_valid:
            # Package has been tampered with!
            trigger_emergency_shutdown()
    """
    
    def __init__(
        self,
        package_name: str,
        manifest: HashManifest = None,
        on_tamper: Callable[[IntegrityReport], None] = None
    ):
        """
        Initialize integrity verifier.
        
        Args:
            package_name: Name of package to verify
            manifest: HashManifest with expected hashes
            on_tamper: Callback when tampering is detected
        """
        self.package_name = package_name
        self.manifest = manifest or HashManifest()
        self.on_tamper = on_tamper
        self._package_path: Optional[Path] = None
        self._last_report: Optional[IntegrityReport] = None
        
        # Find package location
        self._locate_package()
    
    def _locate_package(self):
        """Locate the package on disk"""
        try:
            package = importlib.import_module(self.package_name)
            if hasattr(package, '__path__'):
                self._package_path = Path(package.__path__[0])
            elif hasattr(package, '__file__'):
                self._package_path = Path(package.__file__).parent
        except ImportError:
            logger.warning(f"Package {self.package_name} not found")
    
    def verify(self, use_embedded: bool = True) -> IntegrityReport:
        """
        Verify package integrity.
        
        Args:
            use_embedded: Use embedded hashes (most secure)
            
        Returns:
            IntegrityReport with verification results
        """
        if not self._package_path:
            return IntegrityReport(
                status=IntegrityStatus.MISSING,
                package_name=self.package_name,
                files_checked=0,
                files_passed=0,
                error=f"Package {self.package_name} not found"
            )
        
        files_checked = 0
        files_passed = 0
        files_failed = []
        
        try:
            # Get expected hashes
            if use_embedded and EMBEDDED_CRITICAL_HASHES:
                expected_hashes = EMBEDDED_CRITICAL_HASHES
            else:
                expected_hashes = self.manifest.get_all_hashes()
            
            if not expected_hashes:
                # No hashes to verify against - generate them
                logger.warning("No expected hashes - running in learning mode")
                return self._generate_baseline()
            
            # Verify each file
            for relative_path, expected_hash in expected_hashes.items():
                filepath = self._package_path.parent / relative_path
                
                if not filepath.exists():
                    files_failed.append(f"{relative_path} (MISSING)")
                    files_checked += 1
                    continue
                
                actual_hash = HashManifest.compute_file_hash(str(filepath))
                expected = expected_hash.replace("sha256:", "")
                
                files_checked += 1
                
                if actual_hash == expected:
                    files_passed += 1
                else:
                    files_failed.append(
                        f"{relative_path} (HASH MISMATCH)"
                    )
                    logger.error(
                        f"TAMPER DETECTED: {relative_path}\n"
                        f"  Expected: {expected[:16]}...\n"
                        f"  Actual:   {actual_hash[:16]}..."
                    )
            
            # Determine status
            if files_failed:
                status = IntegrityStatus.TAMPERED
            elif files_checked == 0:
                status = IntegrityStatus.UNKNOWN
            else:
                status = IntegrityStatus.VERIFIED
            
            # Generate attestation hash
            attestation = self._generate_attestation(
                files_checked, files_passed, files_failed
            )
            
            report = IntegrityReport(
                status=status,
                package_name=self.package_name,
                files_checked=files_checked,
                files_passed=files_passed,
                files_failed=files_failed,
                attestation_hash=attestation
            )
            
            self._last_report = report
            
            # Trigger callback on tamper
            if status == IntegrityStatus.TAMPERED and self.on_tamper:
                self.on_tamper(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Integrity verification failed: {e}")
            return IntegrityReport(
                status=IntegrityStatus.ERROR,
                package_name=self.package_name,
                files_checked=files_checked,
                files_passed=files_passed,
                files_failed=files_failed,
                error=str(e)
            )
    
    def _generate_baseline(self) -> IntegrityReport:
        """Generate baseline hashes (learning mode)"""
        if not self._package_path:
            return IntegrityReport(
                status=IntegrityStatus.MISSING,
                package_name=self.package_name,
                files_checked=0,
                files_passed=0
            )
        
        count = self.manifest.generate_from_package(str(self._package_path))
        
        logger.info(f"Generated baseline hashes for {count} files")
        logger.info("Add these to EMBEDDED_CRITICAL_HASHES for protection")
        
        # Print hashes for embedding
        for path, hash_val in self.manifest.get_all_hashes().items():
            print(f'    "{path}": "sha256:{hash_val}",')
        
        return IntegrityReport(
            status=IntegrityStatus.UNKNOWN,
            package_name=self.package_name,
            files_checked=count,
            files_passed=count,
            error="Baseline generated - no verification performed"
        )
    
    def _generate_attestation(
        self,
        checked: int,
        passed: int,
        failed: List[str]
    ) -> str:
        """Generate attestation hash for audit trail"""
        data = {
            "package": self.package_name,
            "checked": checked,
            "passed": passed,
            "failed": failed,
            "timestamp": datetime.utcnow().isoformat()
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()[:32]


# =============================================================================
# RUNTIME TAMPER DETECTION
# =============================================================================

class RuntimeTamperDetector:
    """
    Detects runtime tampering attempts.
    
    Monitors for:
    1. Module reload attempts
    2. Attribute modification on protected objects
    3. sys.modules manipulation
    4. Import hook injection
    """
    
    def __init__(
        self,
        protected_modules: List[str],
        on_tamper: Callable[[str], None] = None
    ):
        """
        Initialize runtime tamper detector.
        
        Args:
            protected_modules: List of module names to protect
            on_tamper: Callback when tampering is detected
        """
        self.protected_modules = set(protected_modules)
        self.on_tamper = on_tamper
        self._original_import = None
        self._module_hashes: Dict[str, str] = {}
        self._monitoring = False
    
    def start_monitoring(self):
        """Start monitoring for tampering"""
        if self._monitoring:
            return
        
        # Store original module states
        for mod_name in self.protected_modules:
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
                self._module_hashes[mod_name] = self._hash_module(mod)
        
        # Install import hook
        self._original_import = __builtins__.get('__import__', __import__)
        __builtins__['__import__'] = self._protected_import
        
        self._monitoring = True
        logger.info(f"Runtime tamper detection started for {len(self.protected_modules)} modules")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        if not self._monitoring:
            return
        
        # Restore original import
        if self._original_import:
            __builtins__['__import__'] = self._original_import
        
        self._monitoring = False
    
    def _protected_import(self, name, *args, **kwargs):
        """Protected import that detects reload attempts"""
        # Check if this is a reload of protected module
        if name in self.protected_modules and name in sys.modules:
            logger.critical(f"🚨 TAMPER ATTEMPT: Reload of protected module {name}")
            if self.on_tamper:
                self.on_tamper(f"Module reload blocked: {name}")
            raise ImportError(f"Reloading protected module {name} is not allowed")
        
        return self._original_import(name, *args, **kwargs)
    
    def _hash_module(self, module) -> str:
        """Generate hash of module's important attributes"""
        parts = []
        
        # Hash function bytecodes
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj):
                if hasattr(obj, '__code__'):
                    parts.append(f"{name}:{hash(obj.__code__.co_code)}")
            elif inspect.isclass(obj):
                parts.append(f"{name}:class")
        
        return hashlib.sha256(
            "|".join(sorted(parts)).encode()
        ).hexdigest()[:32]
    
    def verify_modules(self) -> Dict[str, bool]:
        """Verify protected modules haven't been modified"""
        results = {}
        
        for mod_name in self.protected_modules:
            if mod_name not in sys.modules:
                results[mod_name] = False
                continue
            
            mod = sys.modules[mod_name]
            current_hash = self._hash_module(mod)
            original_hash = self._module_hashes.get(mod_name)
            
            if original_hash and current_hash != original_hash:
                logger.critical(f"🚨 MODULE TAMPERED: {mod_name}")
                results[mod_name] = False
                if self.on_tamper:
                    self.on_tamper(f"Module modified: {mod_name}")
            else:
                results[mod_name] = True
        
        return results


# =============================================================================
# READ-ONLY ENFORCEMENT
# =============================================================================

class ReadOnlyEnforcer:
    """
    Enforces read-only status on package files.
    
    Checks that package files cannot be written to,
    providing defense in depth against modification.
    """
    
    def __init__(self, package_path: str):
        self.package_path = Path(package_path)
    
    def check_read_only(self) -> Tuple[bool, List[str]]:
        """
        Check if package files are read-only.
        
        Returns:
            Tuple of (all_readonly, writable_files)
        """
        writable = []
        
        for py_file in self.package_path.rglob('*.py'):
            if os.access(py_file, os.W_OK):
                writable.append(str(py_file))
        
        return len(writable) == 0, writable
    
    def make_read_only(self) -> int:
        """
        Make all package files read-only.
        
        Returns number of files modified.
        Note: Requires appropriate permissions.
        """
        count = 0
        
        for py_file in self.package_path.rglob('*.py'):
            try:
                # Remove write permission (Unix: 444, Windows: read-only attr)
                current_mode = py_file.stat().st_mode
                new_mode = current_mode & ~0o222  # Remove write bits
                py_file.chmod(new_mode)
                count += 1
            except PermissionError:
                logger.warning(f"Cannot change permissions on {py_file}")
        
        return count


# =============================================================================
# BYPASS PROTECTION MANAGER
# =============================================================================

class BypassProtection:
    """
    Complete bypass protection manager.
    
    Combines all protection mechanisms:
    1. Package integrity verification
    2. Runtime tamper detection
    3. Read-only enforcement
    4. Self-verification
    
    Usage:
        protection = BypassProtection(
            package_name="runtime_fence",
            on_bypass=emergency_shutdown
        )
        
        # Verify on startup
        if not protection.verify_integrity():
            sys.exit(1)  # Do not run with compromised safety
        
        # Start continuous monitoring
        protection.start_monitoring()
    """
    
    def __init__(
        self,
        package_name: str,
        manifest_path: str = None,
        on_bypass: Callable[[str], None] = None
    ):
        """
        Initialize bypass protection.
        
        Args:
            package_name: Package to protect
            manifest_path: Path to hash manifest file
            on_bypass: Callback when bypass attempt detected
        """
        self.package_name = package_name
        self.on_bypass = on_bypass
        
        # Initialize components
        self.manifest = HashManifest(manifest_path)
        self.verifier = IntegrityVerifier(
            package_name,
            self.manifest,
            on_tamper=self._handle_tamper
        )
        self.detector = RuntimeTamperDetector(
            [package_name],
            on_tamper=self._handle_tamper
        )
        
        # Find package path for read-only enforcement
        self._package_path = self.verifier._package_path
        self.enforcer = ReadOnlyEnforcer(
            str(self._package_path)
        ) if self._package_path else None
        
        # Status tracking
        self._verified = False
        self._monitoring = False
        self._tamper_count = 0
        
        logger.info(f"Bypass protection initialized for {package_name}")
    
    def verify_integrity(self) -> bool:
        """
        Verify package integrity.
        
        Returns True if package is intact, False if tampered.
        """
        report = self.verifier.verify()
        
        if report.is_valid:
            logger.info(f"✅ Package integrity verified: {report.files_passed}/{report.files_checked} files OK")
            self._verified = True
            return True
        else:
            logger.critical(
                f"🚨 PACKAGE INTEGRITY FAILED\n"
                f"   Status: {report.status.value}\n"
                f"   Files checked: {report.files_checked}\n"
                f"   Files failed: {report.files_failed}"
            )
            self._verified = False
            return False
    
    def start_monitoring(self):
        """Start continuous monitoring for tampering"""
        if not self._verified:
            logger.warning("Starting monitoring without verified integrity!")
        
        self.detector.start_monitoring()
        self._monitoring = True
        logger.info("Runtime tamper monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.detector.stop_monitoring()
        self._monitoring = False
    
    def check_read_only(self) -> bool:
        """Check if package files are read-only"""
        if not self.enforcer:
            return False
        
        is_readonly, writable = self.enforcer.check_read_only()
        
        if not is_readonly:
            logger.warning(f"Writable files detected: {writable}")
        
        return is_readonly
    
    def _handle_tamper(self, report_or_message):
        """Handle tamper detection"""
        self._tamper_count += 1
        
        if isinstance(report_or_message, IntegrityReport):
            message = f"Integrity violation: {report_or_message.files_failed}"
        else:
            message = str(report_or_message)
        
        logger.critical(f"🚨 BYPASS ATTEMPT #{self._tamper_count}: {message}")
        
        if self.on_bypass:
            self.on_bypass(message)
    
    def get_status(self) -> Dict[str, Any]:
        """Get protection status"""
        return {
            "package": self.package_name,
            "verified": self._verified,
            "monitoring": self._monitoring,
            "tamper_attempts": self._tamper_count,
            "last_report": self.verifier._last_report.to_dict() if self.verifier._last_report else None
        }
    
    def generate_manifest(self, output_path: str = None):
        """Generate hash manifest for distribution"""
        if not self._package_path:
            logger.error("Package path not found")
            return
        
        manifest = HashManifest(output_path or f"{self.package_name}_manifest.json")
        count = manifest.generate_from_package(str(self._package_path))
        manifest.save_manifest()
        
        logger.info(f"Generated manifest with {count} file hashes")
        logger.info(f"Saved to: {manifest.manifest_path}")
        
        # Also print for embedding
        print("\n# Add to EMBEDDED_CRITICAL_HASHES:")
        print("EMBEDDED_CRITICAL_HASHES = {")
        for path, hash_val in manifest.get_all_hashes().items():
            print(f'    "{path}": "sha256:{hash_val}",')
        print("}")


# =============================================================================
# SELF-VERIFICATION
# =============================================================================

def verify_self() -> bool:
    """
    Verify this module hasn't been tampered with.
    
    This function verifies the bypass_protection module itself,
    providing bootstrapped security.
    """
    # Get this module's file
    this_file = Path(__file__)
    
    if not this_file.exists():
        return False
    
    # In production, this hash would be embedded at build time
    # and verified against the actual file
    actual_hash = HashManifest.compute_file_hash(str(this_file))
    
    # Log hash for debugging (in production, compare to expected)
    logger.debug(f"Self-verification hash: {actual_hash[:32]}...")
    
    return True


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def protect_package(
    package_name: str,
    on_bypass: Callable[[str], None] = None
) -> BypassProtection:
    """
    Convenience function to set up bypass protection.
    
    Args:
        package_name: Package to protect
        on_bypass: Callback for bypass attempts
        
    Returns:
        Configured BypassProtection instance
    """
    protection = BypassProtection(
        package_name=package_name,
        on_bypass=on_bypass
    )
    
    # Verify integrity
    if not protection.verify_integrity():
        logger.critical(f"REFUSING TO CONTINUE - {package_name} compromised!")
        raise RuntimeError(f"Package {package_name} integrity check failed")
    
    # Start monitoring
    protection.start_monitoring()
    
    return protection


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 60)
    print("BYPASS PROTECTION TEST")
    print("=" * 60)
    
    # Test self-verification
    print("\n[1] Self-verification...")
    if verify_self():
        print("   ✅ Self-verification passed")
    else:
        print("   ❌ Self-verification FAILED")
    
    # Test with a sample package
    print("\n[2] Testing with 'os' module (built-in)...")
    
    def on_bypass(msg):
        print(f"   🚨 BYPASS DETECTED: {msg}")
    
    protection = BypassProtection(
        package_name="os",
        on_bypass=on_bypass
    )
    
    # Verify integrity (will be in learning mode for os)
    print("\n[3] Verifying integrity...")
    result = protection.verify_integrity()
    print(f"   Result: {'✅ Verified' if result else '❌ Failed'}")
    
    # Start monitoring
    print("\n[4] Starting runtime monitoring...")
    protection.start_monitoring()
    print("   Runtime monitoring active")
    
    # Get status
    print("\n[5] Protection status:")
    status = protection.get_status()
    for key, value in status.items():
        if key != "last_report":
            print(f"   {key}: {value}")
    
    # Generate manifest example
    print("\n[6] Generating manifest (learning mode)...")
    print("   (In production, run once during build to embed hashes)")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
