"""
Feature Flags Infrastructure

This module provides a simple feature flag system for safe rollout of refactored code.
Flags can be configured via environment variables or settings.
"""

from typing import Dict, Optional, Callable, Any
from enum import Enum
import os
from functools import wraps
from app.core.logging import logger


class FeatureFlag(str, Enum):
    """Enumeration of all feature flags in the system"""
    USE_NEW_WEBSOCKET_HANDLER = "use_new_websocket_handler"
    USE_PERMISSION_SERVICE = "use_permission_service"
    USE_CONTAINER_STATS_CALCULATOR = "use_container_stats_calculator"
    USE_DECORATOR_PATTERN = "use_decorator_pattern"
    USE_LOG_BUFFER_SERVICE = "use_log_buffer_service"


class FeatureFlagService:
    """Service for managing feature flags"""
    
    def __init__(self):
        self._flags: Dict[str, bool] = {}
        self._default_values = {
            FeatureFlag.USE_NEW_WEBSOCKET_HANDLER: False,
            FeatureFlag.USE_PERMISSION_SERVICE: False,
            FeatureFlag.USE_CONTAINER_STATS_CALCULATOR: False,
            FeatureFlag.USE_DECORATOR_PATTERN: False,
            FeatureFlag.USE_LOG_BUFFER_SERVICE: False,
        }
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load feature flags from environment variables"""
        for flag in FeatureFlag:
            env_key = f"FEATURE_{flag.value.upper()}"
            env_value = os.getenv(env_key)
            if env_value is not None:
                self._flags[flag] = env_value.lower() in ('true', '1', 'yes', 'on')
                logger.info(f"Feature flag {flag.value} set to {self._flags[flag]} from environment")
    
    def is_enabled(self, flag: FeatureFlag) -> bool:
        """Check if a feature flag is enabled"""
        if flag in self._flags:
            return self._flags[flag]
        return self._default_values.get(flag, False)
    
    def set_flag(self, flag: FeatureFlag, enabled: bool):
        """Programmatically set a feature flag (useful for testing)"""
        self._flags[flag] = enabled
        logger.info(f"Feature flag {flag.value} set to {enabled}")
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get current state of all feature flags"""
        result = {}
        for flag in FeatureFlag:
            result[flag.value] = self.is_enabled(flag)
        return result


# Global instance
_feature_flags = FeatureFlagService()


def is_feature_enabled(flag: FeatureFlag) -> bool:
    """Check if a feature flag is enabled"""
    return _feature_flags.is_enabled(flag)


def set_feature_flag(flag: FeatureFlag, enabled: bool):
    """Set a feature flag (mainly for testing)"""
    _feature_flags.set_flag(flag, enabled)


def get_all_feature_flags() -> Dict[str, bool]:
    """Get all feature flags and their current state"""
    return _feature_flags.get_all_flags()


def feature_flag(flag: FeatureFlag, fallback: Optional[Callable] = None):
    """
    Decorator to conditionally execute functions based on feature flags
    
    Usage:
        @feature_flag(FeatureFlag.USE_NEW_WEBSOCKET_HANDLER)
        def new_handler():
            return "new implementation"
        
        @feature_flag(FeatureFlag.USE_NEW_WEBSOCKET_HANDLER, fallback=old_handler)
        def new_handler():
            return "new implementation"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if is_feature_enabled(flag):
                return func(*args, **kwargs)
            elif fallback:
                return fallback(*args, **kwargs)
            else:
                raise RuntimeError(f"Feature {flag.value} is disabled and no fallback provided")
        return wrapper
    return decorator


def with_feature_flag(flag: FeatureFlag, 
                      when_enabled: Callable[[], Any], 
                      when_disabled: Callable[[], Any]) -> Any:
    """
    Execute different code paths based on feature flag state
    
    Usage:
        result = with_feature_flag(
            FeatureFlag.USE_NEW_IMPLEMENTATION,
            when_enabled=lambda: new_implementation(),
            when_disabled=lambda: old_implementation()
        )
    """
    if is_feature_enabled(flag):
        return when_enabled()
    else:
        return when_disabled()