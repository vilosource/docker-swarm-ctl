#!/usr/bin/env python3
"""
Feature Flag Management Script

Usage:
    python manage_feature_flags.py --list                # List all feature flags
    python manage_feature_flags.py --enable-all          # Enable all refactored features
    python manage_feature_flags.py --disable-all         # Disable all refactored features
    python manage_feature_flags.py --enable <flag>       # Enable specific flag
    python manage_feature_flags.py --disable <flag>      # Disable specific flag
"""

import os
import sys
import argparse
from pathlib import Path


# Feature flag names
FEATURE_FLAGS = [
    "FEATURE_USE_NEW_WEBSOCKET_HANDLER",
    "FEATURE_USE_PERMISSION_SERVICE",
    "FEATURE_USE_CONTAINER_STATS_CALCULATOR",
    "FEATURE_USE_DECORATOR_PATTERN",
    "FEATURE_USE_LOG_BUFFER_SERVICE",
]

# Descriptions
FLAG_DESCRIPTIONS = {
    "FEATURE_USE_NEW_WEBSOCKET_HANDLER": "New WebSocket handler with reduced complexity",
    "FEATURE_USE_PERMISSION_SERVICE": "Centralized permission service with policies",
    "FEATURE_USE_CONTAINER_STATS_CALCULATOR": "Extracted container stats calculation",
    "FEATURE_USE_DECORATOR_PATTERN": "API endpoint decorators for cross-cutting concerns",
    "FEATURE_USE_LOG_BUFFER_SERVICE": "Centralized log buffer management service",
}


def update_docker_compose(enable_all=False, disable_all=False, enable_flag=None, disable_flag=None):
    """Update docker-compose.yml with feature flag values"""
    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"
    
    if not compose_path.exists():
        print(f"Error: docker-compose.yml not found at {compose_path}")
        sys.exit(1)
    
    with open(compose_path, 'r') as f:
        lines = f.readlines()
    
    updated_lines = []
    for line in lines:
        updated_line = line
        
        for flag in FEATURE_FLAGS:
            if f"{flag}:" in line:
                if enable_all or (enable_flag and flag == enable_flag):
                    updated_line = f"      {flag}: \"true\"\n"
                elif disable_all or (disable_flag and flag == disable_flag):
                    updated_line = f"      {flag}: \"false\"\n"
        
        updated_lines.append(updated_line)
    
    with open(compose_path, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"Updated {compose_path}")


def list_flags():
    """List all feature flags and their current status"""
    print("\nFeature Flags:")
    print("-" * 80)
    
    for flag in FEATURE_FLAGS:
        env_value = os.environ.get(flag, "false")
        status = "✅ Enabled" if env_value.lower() == "true" else "❌ Disabled"
        description = FLAG_DESCRIPTIONS.get(flag, "")
        print(f"{flag:<40} {status:<15} {description}")
    
    print("-" * 80)
    print("\nTo check current values in docker-compose.yml, run:")
    print("  grep FEATURE_ docker-compose.yml")
    print("\nTo apply changes, restart the containers:")
    print("  docker compose restart backend celery")


def main():
    parser = argparse.ArgumentParser(description="Manage feature flags for refactored code")
    parser.add_argument("--list", action="store_true", help="List all feature flags")
    parser.add_argument("--enable-all", action="store_true", help="Enable all feature flags")
    parser.add_argument("--disable-all", action="store_true", help="Disable all feature flags")
    parser.add_argument("--enable", help="Enable specific feature flag")
    parser.add_argument("--disable", help="Disable specific feature flag")
    
    args = parser.parse_args()
    
    if args.list:
        list_flags()
    elif args.enable_all:
        update_docker_compose(enable_all=True)
        print("✅ All feature flags enabled in docker-compose.yml")
        print("Restart containers to apply changes: docker compose restart backend celery")
    elif args.disable_all:
        update_docker_compose(disable_all=True)
        print("❌ All feature flags disabled in docker-compose.yml")
        print("Restart containers to apply changes: docker compose restart backend celery")
    elif args.enable:
        if args.enable in FEATURE_FLAGS:
            update_docker_compose(enable_flag=args.enable)
            print(f"✅ {args.enable} enabled in docker-compose.yml")
            print("Restart containers to apply changes: docker compose restart backend celery")
        else:
            print(f"Error: Unknown flag {args.enable}")
            print(f"Valid flags: {', '.join(FEATURE_FLAGS)}")
    elif args.disable:
        if args.disable in FEATURE_FLAGS:
            update_docker_compose(disable_flag=args.disable)
            print(f"❌ {args.disable} disabled in docker-compose.yml")
            print("Restart containers to apply changes: docker compose restart backend celery")
        else:
            print(f"Error: Unknown flag {args.disable}")
            print(f"Valid flags: {', '.join(FEATURE_FLAGS)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()