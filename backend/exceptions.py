"""
Custom Exceptions - Application-specific exception classes
"""


class PostpartumException(Exception):
    """Base exception for Postpartum application"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(PostpartumException):
    """Authentication related errors"""
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, "AUTH_ERROR", details)


class ValidationError(PostpartumException):
    """Validation errors"""
    def __init__(self, message: str = "Validation failed", details: dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class AIServiceError(PostpartumException):
    """AI service related errors"""
    def __init__(self, message: str = "AI service error", details: dict = None):
        super().__init__(message, "AI_SERVICE_ERROR", details)


class TaskQueueError(PostpartumException):
    """Task queue related errors"""
    def __init__(self, message: str = "Task queue error", details: dict = None):
        super().__init__(message, "TASK_QUEUE_ERROR", details)


class DatabaseError(PostpartumException):
    """Database related errors"""
    def __init__(self, message: str = "Database error", details: dict = None):
        super().__init__(message, "DATABASE_ERROR", details)


class RateLimitError(PostpartumException):
    """Rate limit exceeded errors"""
    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class NotFoundError(PostpartumException):
    """Resource not found errors"""
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message, "NOT_FOUND_ERROR", details)


class AuthorizationError(PostpartumException):
    """Authorization related errors (user lacks permission)"""
    def __init__(self, message: str = "Authorization failed", details: dict = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class ConflictError(PostpartumException):
    """Resource conflict errors (e.g., duplicate resource)"""
    def __init__(self, message: str = "Resource conflict", details: dict = None):
        super().__init__(message, "CONFLICT_ERROR", details)


class ServiceUnavailableError(PostpartumException):
    """Service unavailable errors"""
    def __init__(self, message: str = "Service unavailable", details: dict = None):
        super().__init__(message, "SERVICE_UNAVAILABLE", details)

