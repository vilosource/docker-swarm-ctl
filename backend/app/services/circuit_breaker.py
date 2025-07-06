"""
Circuit Breaker Pattern Implementation

Provides resilience for Docker operations by preventing cascading failures
when a Docker host becomes unresponsive.
"""

from typing import Optional, Dict, Any, Callable, TypeVar
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from enum import Enum

from app.core.logging import logger
from app.core.exceptions import DockerConnectionError


T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures exceeded threshold
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold  # Failures before opening
        self.recovery_timeout = recovery_timeout    # Seconds before trying again
        self.expected_exception = expected_exception  # Exception type to catch
        self.success_threshold = success_threshold  # Successes needed to close


class CircuitBreaker:
    """
    Circuit breaker implementation
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function through circuit breaker"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    await self._transition_to_half_open()
                else:
                    raise DockerConnectionError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable after {self.failure_count} failures."
                    )
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.config.expected_exception as e:
            await self._on_failure()
            raise
    
    async def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure > timedelta(seconds=self.config.recovery_timeout)
    
    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    await self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0  # Reset failure count on success
    
    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                await self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.utcnow()
        self.success_count = 0
        logger.warning(
            f"Circuit breaker '{self.name}' transitioned to OPEN. "
            f"Failure count: {self.failure_count}"
        )
    
    async def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.utcnow()
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED")
    
    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.utcnow()
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold
            }
        }
    
    async def reset(self):
        """Manually reset the circuit breaker"""
        async with self._lock:
            await self._transition_to_closed()
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerManager:
    """Manages circuit breakers for different services/hosts"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=DockerConnectionError,
            success_threshold=2
        )
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker"""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name,
                config or self._default_config
            )
        return self._breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()
    
    async def reset(self, name: str):
        """Reset specific circuit breaker"""
        if name in self._breakers:
            await self._breakers[name].reset()


# Global circuit breaker manager
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager"""
    return _circuit_breaker_manager


def with_circuit_breaker(
    breaker_name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """
    Decorator to apply circuit breaker to a function
    
    Usage:
        @with_circuit_breaker("docker-host-1")
        async def connect_to_docker():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = manager.get_or_create(breaker_name, config)
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator