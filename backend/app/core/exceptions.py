from typing import Optional, Dict, Any
from fastapi import status


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, status.HTTP_401_UNAUTHORIZED, details)


class InvalidCredentialsError(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid email or password", "INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    def __init__(self):
        super().__init__("Token has expired", "TOKEN_EXPIRED")


class TokenInvalidError(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid token", "TOKEN_INVALID")


class AuthorizationError(AppException):
    def __init__(self, message: str = "Access denied", code: str = "AUTHORIZATION_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN, details)


class InsufficientPermissionsError(AuthorizationError):
    def __init__(self, required_role: str):
        super().__init__(
            f"Insufficient permissions. Required role: {required_role}",
            "INSUFFICIENT_PERMISSIONS",
            {"required_role": required_role}
        )


class ResourceAccessDeniedError(AuthorizationError):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"Access denied to {resource_type} with id {resource_id}",
            "RESOURCE_ACCESS_DENIED",
            {"resource_type": resource_type, "resource_id": resource_id}
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", code: str = "VALIDATION_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, status.HTTP_400_BAD_REQUEST, details)


class InvalidInputError(ValidationError):
    def __init__(self, field: str, message: str):
        super().__init__(
            f"Invalid input for field '{field}': {message}",
            "INVALID_INPUT",
            {"field": field}
        )


class MissingRequiredFieldError(ValidationError):
    def __init__(self, field: str):
        super().__init__(
            f"Missing required field: {field}",
            "MISSING_REQUIRED_FIELD",
            {"field": field}
        )


class ResourceError(AppException):
    pass


class ResourceNotFoundError(ResourceError):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with id {resource_id} not found",
            "RESOURCE_NOT_FOUND",
            status.HTTP_404_NOT_FOUND,
            {"resource_type": resource_type, "resource_id": resource_id}
        )


class ResourceConflictError(ResourceError):
    def __init__(self, resource_type: str, message: str):
        super().__init__(
            message,
            "RESOURCE_CONFLICT",
            status.HTTP_409_CONFLICT,
            {"resource_type": resource_type}
        )


class ExternalServiceError(AppException):
    pass


class DockerConnectionError(ExternalServiceError):
    def __init__(self, message: str = "Failed to connect to Docker daemon"):
        super().__init__(message, "DOCKER_CONNECTION_ERROR", status.HTTP_503_SERVICE_UNAVAILABLE)


class DockerOperationError(ExternalServiceError):
    def __init__(self, operation: str, message: str):
        super().__init__(
            f"Docker operation '{operation}' failed: {message}",
            "DOCKER_OPERATION_ERROR",
            status.HTTP_502_BAD_GATEWAY,
            {"operation": operation}
        )


class DatabaseConnectionError(ExternalServiceError):
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message, "DATABASE_CONNECTION_ERROR", status.HTTP_503_SERVICE_UNAVAILABLE)