"""Configuration management for the CLI"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ContextConfig:
    """Configuration for a single context"""
    api_url: str
    username: Optional[str] = None
    token: Optional[str] = None
    verify_ssl: bool = True


@dataclass
class Config:
    """Main configuration structure"""
    contexts: Dict[str, ContextConfig] = field(default_factory=dict)
    current_context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for YAML serialization"""
        return {
            'contexts': {
                name: {
                    'api_url': ctx.api_url,
                    'username': ctx.username,
                    'token': ctx.token,
                    'verify_ssl': ctx.verify_ssl
                }
                for name, ctx in self.contexts.items()
            },
            'current_context': self.current_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary"""
        contexts = {}
        for name, ctx_data in data.get('contexts', {}).items():
            contexts[name] = ContextConfig(
                api_url=ctx_data.get('api_url'),
                username=ctx_data.get('username'),
                token=ctx_data.get('token'),
                verify_ssl=ctx_data.get('verify_ssl', True)
            )
        
        return cls(
            contexts=contexts,
            current_context=data.get('current_context')
        )


class ConfigManager:
    """Manages configuration file operations"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        
    def ensure_config_dir(self):
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def load(self) -> Config:
        """Load configuration from file"""
        if not self.config_path.exists():
            # Return default config
            return Config()
        
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                return Config.from_dict(data)
        except Exception as e:
            # Return default config on error
            print(f"Warning: Failed to load config: {e}")
            return Config()
    
    def save(self, config: Config):
        """Save configuration to file"""
        self.ensure_config_dir()
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False)
    
    def add_context(self, name: str, api_url: str, username: Optional[str] = None,
                   token: Optional[str] = None, verify_ssl: bool = True):
        """Add or update a context"""
        config = self.load()
        config.contexts[name] = ContextConfig(
            api_url=api_url,
            username=username,
            token=token,
            verify_ssl=verify_ssl
        )
        
        # Set as current if it's the first context
        if not config.current_context:
            config.current_context = name
        
        self.save(config)
    
    def remove_context(self, name: str):
        """Remove a context"""
        config = self.load()
        if name in config.contexts:
            del config.contexts[name]
            
            # Update current context if needed
            if config.current_context == name:
                config.current_context = next(iter(config.contexts), None)
            
            self.save(config)
    
    def use_context(self, name: str):
        """Switch to a different context"""
        config = self.load()
        if name in config.contexts:
            config.current_context = name
            self.save(config)
            return True
        return False
    
    def update_token(self, context_name: str, token: str):
        """Update token for a context"""
        config = self.load()
        if context_name in config.contexts:
            config.contexts[context_name].token = token
            self.save(config)