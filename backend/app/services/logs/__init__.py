"""
Unified Log Streaming Architecture

This module provides a unified, extensible architecture for streaming logs from
various sources including Docker containers, Swarm services, host systems, and more.
"""

from .base import (
    LogEntry,
    LogSourceMetadata,
    LogSource,
    LogLevel,
    LogSourceType
)

__all__ = [
    'LogEntry',
    'LogSourceMetadata', 
    'LogSource',
    'LogLevel',
    'LogSourceType'
]