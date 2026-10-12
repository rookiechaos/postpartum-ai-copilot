"""
Logging Service - Enterprise-grade logging and error tracking
"""

import logging
import sys
import re
from datetime import datetime
from typing import Optional, Dict, Any
import json
import traceback
from pathlib import Path
import os

from utils.runtime_paths import resolve_runtime_path

LOG_DIR = resolve_runtime_path(os.getenv("LOG_DIR", "do-not-upload/logs"), "logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_HOME_PATH_PATTERN = re.compile(r"(/Users/|/home/)[^/\s\"']+")


def sanitize_log_path(text: str) -> str:
    """Redact OS username segments from paths before writing logs."""
    if not text:
        return text
    return _HOME_PATH_PATTERN.sub(r"\1<redacted>", text)


class SanitizedFormatter(logging.Formatter):
    """Logging formatter that redacts home-directory paths."""

    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, "pathname", None):
            record.pathname = sanitize_log_path(record.pathname)
        return sanitize_log_path(super().format(record))


class StructuredLogger:
    """Structured logging for enterprise applications"""
    
    def __init__(self, name: str = "postpartum"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler for errors
        error_file = LOG_DIR / "error.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        error_format = SanitizedFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
        )
        error_handler.setFormatter(error_format)
        self.logger.addHandler(error_handler)
        
        # File handler for all logs
        all_logs_file = LOG_DIR / "app.log"
        all_logs_handler = logging.FileHandler(all_logs_file)
        all_logs_handler.setLevel(logging.INFO)
        all_logs_handler.setFormatter(error_format)
        self.logger.addHandler(all_logs_handler)
    
    def log_api_request(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str],
        status_code: int,
        response_time_ms: int,
        error: Optional[str] = None
    ):
        """Log API request with structured data"""
        log_data = {
            "event": "api_request",
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "error": error
        }
        
        if error or status_code >= 400:
            self.logger.error(f"API request: {json.dumps(log_data)}")
        else:
            self.logger.info(f"API request: {json.dumps(log_data)}")
    
    def log_ai_request(
        self,
        user_id: str,
        provider: str,
        query_length: int,
        response_time_ms: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Log AI service request"""
        log_data = {
            "event": "ai_request",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "provider": provider,
            "query_length": query_length,
            "response_time_ms": response_time_ms,
            "success": success,
            "error": error
        }
        
        if error or not success:
            self.logger.error(f"AI request: {json.dumps(log_data)}")
        else:
            self.logger.info(f"AI request: {json.dumps(log_data)}")
    
    def log_task_event(
        self,
        task_id: str,
        task_type: str,
        user_id: str,
        event_type: str,  # created, started, completed, failed
        duration_ms: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Log task queue event"""
        log_data = {
            "event": "task_event",
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "task_type": task_type,
            "user_id": user_id,
            "event_type": event_type,
            "duration_ms": duration_ms,
            "error": error
        }
        
        if error or event_type == "failed":
            self.logger.error(f"Task event: {json.dumps(log_data)}")
        else:
            self.logger.info(f"Task event: {json.dumps(log_data)}")
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ):
        """
        Log error with sensitive data filtering
        
        Automatically filters out sensitive information from context
        """
        # Filter sensitive data from context
        if context:
            from services.code_security_audit import CodeSecurityAuditor
            filtered_context = {}
            for key, value in context.items():
                # Check if key or value contains sensitive data
                key_str = str(key).lower()
                value_str = str(value) if value else ""
                
                # Skip sensitive keys
                sensitive_keys = ['password', 'secret', 'token', 'api_key', 'apikey', 'key']
                if any(sk in key_str for sk in sensitive_keys):
                    filtered_context[key] = "[REDACTED]"
                    continue
                
                # Check value for sensitive patterns
                is_safe, warnings = CodeSecurityAuditor.check_sensitive_data_logging(value_str)
                if not is_safe:
                    filtered_context[key] = "[REDACTED]"
                else:
                    filtered_context[key] = value
            
            context = filtered_context
        
        error_data = {
            "event": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": sanitize_log_path(str(error)),
            # A handler may replace an unsafe exception with a safe one. Never
            # include the ambient exception or its request input through a chain.
            "traceback": sanitize_log_path("".join(traceback.format_exception(
                type(error), error, error.__traceback__, chain=False
            ))),
            "user_id": user_id,
            "context": context or {}
        }
        
        self.logger.error(f"Error: {json.dumps(error_data, default=str)}")
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log user action"""
        log_data = {
            "event": "user_action",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
        
        self.logger.info(f"User action: {json.dumps(log_data)}")
    
    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        log_data = {
            "event": "security",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,  # login_failed, rate_limit_exceeded, etc.
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {}
        }
        
        self.logger.warning(f"Security event: {json.dumps(log_data)}")
    
    def log_performance(
        self,
        metric_name: str,
        value: float,
        unit: str = "ms",
        context: Optional[Dict[str, Any]] = None
    ):
        """Log performance metric"""
        log_data = {
            "event": "performance",
            "timestamp": datetime.utcnow().isoformat(),
            "metric": metric_name,
            "value": value,
            "unit": unit,
            "context": context or {}
        }
        
        self.logger.info(f"Performance: {json.dumps(log_data)}")
    
    def log_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message"""
        log_data = {
            "event": "info",
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "context": context or {}
        }
        self.logger.info(f"Info: {json.dumps(log_data)}")
    
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        log_data = {
            "event": "warning",
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "context": context or {}
        }
        self.logger.warning(f"Warning: {json.dumps(log_data)}")


# Global logger instance
logger = StructuredLogger()

