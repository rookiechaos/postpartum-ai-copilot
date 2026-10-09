"""
Code Security Audit - Static analysis for security vulnerabilities
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from services.security_validator import InputSanitizer


class CodeSecurityAuditor:
    """Audit code for security vulnerabilities"""
    
    @staticmethod
    def validate_file_path(path: str, base_dir: str = None) -> Tuple[bool, str]:
        """
        Validate file path to prevent path traversal attacks
        
        Args:
            path: File path to validate
            base_dir: Base directory to restrict paths to
        
        Returns:
            (is_valid, error_message)
        """
        if not path:
            return False, "Path cannot be empty"
        
        # Normalize path
        normalized = os.path.normpath(path)
        
        # Check for path traversal attempts
        if ".." in normalized or normalized.startswith("/"):
            return False, "Path traversal detected"
        
        # If base_dir is provided, ensure path is within it
        if base_dir:
            base_path = Path(base_dir).resolve()
            full_path = (base_path / normalized).resolve()
            
            try:
                full_path.relative_to(base_path)
            except ValueError:
                return False, "Path outside allowed directory"
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '|', '&', ';', '`', '$', '(', ')']
        if any(char in path for char in dangerous_chars):
            return False, "Dangerous characters in path"
        
        return True, None
    
    @staticmethod
    def sanitize_file_path(path: str, base_dir: str = None) -> str:
        """
        Sanitize file path
        
        Args:
            path: File path to sanitize
            base_dir: Base directory
        
        Returns:
            Sanitized path
        """
        # Remove path traversal
        path = path.replace("..", "")
        path = path.replace("//", "/")
        
        # Remove leading slashes
        path = path.lstrip("/")
        
        # Normalize
        path = os.path.normpath(path)
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', '|', '&', ';', '`', '$', '(', ')']
        for char in dangerous_chars:
            path = path.replace(char, "")
        
        # Ensure within base_dir if provided
        if base_dir:
            base_path = Path(base_dir).resolve()
            full_path = (base_path / path).resolve()
            try:
                full_path.relative_to(base_path)
                return str(full_path.relative_to(base_path))
            except ValueError:
                return path  # Return sanitized path even if outside base
        
        return path
    
    @staticmethod
    def check_sql_injection_risk(query: str, user_input: str) -> Tuple[bool, str]:
        """
        Check if query construction is safe
        
        Args:
            query: SQL query string
            user_input: User input being used
        
        Returns:
            (is_safe, warning_message)
        """
        # Check for string formatting with user input
        if f"{{{user_input}}}" in query or f"%s" in query:
            return False, "Potential SQL injection: direct string formatting"
        
        # Check for concatenation
        if "+" in query and user_input in query:
            return False, "Potential SQL injection: string concatenation"
        
        # Safe patterns (using ORM or parameterized queries)
        safe_patterns = [
            r"\.filter\(",
            r"\.query\(",
            r"\.execute\(",
            r"text\(",
        ]
        
        for pattern in safe_patterns:
            if re.search(pattern, query):
                return True, "Using ORM or parameterized query"
        
        return False, "Unsafe query construction detected"
    
    @staticmethod
    def check_sensitive_data_logging(log_message: str) -> Tuple[bool, List[str]]:
        """
        Check if log message contains sensitive data
        
        Args:
            log_message: Log message to check
        
        Returns:
            (is_safe, list_of_warnings)
        """
        warnings = []
        
        # Patterns for sensitive data
        sensitive_patterns = {
            "password": r"(?i)(password|pwd|pass)\s*[:=]\s*['\"]?[^\s'\"]+",
            "token": r"(?i)(token|bearer|jwt)\s*[:=]\s*['\"]?[^\s'\"]+",
            "api_key": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[^\s'\"]+",
            "secret": r"(?i)(secret|secret[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]+",
            "credit_card": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
            "ssn": r"\d{3}-\d{2}-\d{4}",
        }
        
        for pattern_name, pattern in sensitive_patterns.items():
            if re.search(pattern, log_message):
                warnings.append(f"Potential {pattern_name} in log message")
        
        return len(warnings) == 0, warnings
    
    @staticmethod
    def validate_config_path(path: str, allowed_base: str = None) -> Tuple[bool, str]:
        """
        Validate configuration file path
        
        Args:
            path: Configuration path
            allowed_base: Allowed base directory
        
        Returns:
            (is_valid, error_message)
        """
        if not path:
            return False, "Path cannot be empty"
        
        # Check for absolute paths (should be relative or validated)
        if os.path.isabs(path) and allowed_base:
            # Allow absolute paths if they're within allowed_base
            try:
                Path(path).resolve().relative_to(Path(allowed_base).resolve())
            except ValueError:
                return False, "Absolute path outside allowed directory"
        
        # Check for path traversal
        if ".." in path:
            return False, "Path traversal in configuration"
        
        return True, None

