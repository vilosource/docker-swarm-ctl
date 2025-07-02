import argparse
import os
import yaml
import requests

CONFIG_PATH = os.path.expanduser("~/.dsctl/config.yml")

def get_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Configuration file not found at {CONFIG_PATH}")
        exit(1)
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def get_current_context(config):
    current_context_name = config.get('current_context')
    if not current_context_name:
        print("Error: 'current_context' not set in config.")
        exit(1)
    
    for context in config.get('contexts', []):
        if context.get('name') == current_context_name:
            return context
    
    print(f"Error: Context '{current_context_name}' not found in config.")
    exit(1)

def main():
    parser = argparse.ArgumentParser(description="A CLI tool to control Docker Swarm.")
    subparsers = parser.add_subparsers(dest="command")

    # Ping command
    ping_parser = subparsers.add_parser("ping", help="Ping the dsctl-server.")

    # Version command
    version_parser = subparsers.add_parser("version", help="Get server and Docker version.")

    # Cluster info command
    cluster_info_parser = subparsers.add_parser("cluster-info", help="Get cluster information.")

    args = parser.parse_args()

    config = get_config()
    context = get_current_context(config)
    api_url = context.get('api_url')
    token = context.get('token')

    if not api_url or not token:
        print("Error: 'api_url' or 'token' not set in the current context.")
        exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    if args.command == "ping":
        try:
            response = requests.get(f"{api_url}/ping")
            response.raise_for_status()
            print(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    elif args.command == "version":
        try:
            response = requests.get(f"{api_url}/version")
            response.raise_for_status()
            print(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    elif args.command == "cluster-info":
        try:
            response = requests.get(f"{api_url}/cluster/info", headers=headers)
            response.raise_for_status()
            print(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
