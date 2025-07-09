#!/usr/bin/env python3
"""Test script for the Docker Swarm Control CLI"""

import subprocess
import sys


def run_command(cmd):
    """Run a CLI command and print output"""
    print(f"\n$ {cmd}")
    print("-" * 60)
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode


def main():
    """Run CLI tests"""
    print("Docker Swarm Control CLI Test")
    print("=" * 60)
    
    # Show help
    run_command("python -m docker_swarm_ctl.cli --help")
    
    # Show config commands
    run_command("python -m docker_swarm_ctl.cli config --help")
    
    # Add a context
    run_command("python -m docker_swarm_ctl.cli config add-context local --api-url http://localhost:8000/api/v1")
    
    # View config
    run_command("python -m docker_swarm_ctl.cli config view")
    
    # Show auth commands
    run_command("python -m docker_swarm_ctl.cli auth --help")
    
    # Show hosts commands
    run_command("python -m docker_swarm_ctl.cli hosts --help")
    
    # Show swarm commands
    run_command("python -m docker_swarm_ctl.cli swarm --help")
    
    # Show kubectl-style commands
    run_command("python -m docker_swarm_ctl.cli get --help")
    run_command("python -m docker_swarm_ctl.cli create --help")
    run_command("python -m docker_swarm_ctl.cli delete --help")


if __name__ == "__main__":
    main()