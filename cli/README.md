# Docker Swarm Control CLI

A kubectl-like CLI tool for managing Docker Swarm across multiple hosts.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/docker-swarm-ctl/cli.git
cd cli

# Build the binary
make build

# Install to your PATH
make install
```

### Pre-built Binaries

Download the appropriate binary for your platform from the releases page.

## Quick Start

### 1. Configure a context

```bash
# Add a context for your Docker Swarm Control API
docker-swarm-ctl config add-context local --api-url http://localhost:8000/api/v1

# View all contexts
docker-swarm-ctl config view
```

### 2. Login

```bash
# Login to the API
docker-swarm-ctl auth login
```

### 3. Start using the CLI

```bash
# List all Docker hosts
docker-swarm-ctl get hosts

# Get swarm nodes
docker-swarm-ctl get nodes --host <host-id>

# List services
docker-swarm-ctl get services --host <host-id>
```

## Usage Examples

### Host Management

```bash
# List all hosts
docker-swarm-ctl get hosts

# Get specific host details
docker-swarm-ctl get host <host-id>

# Add a new host
docker-swarm-ctl create host --name "docker-1" --url "tcp://192.168.1.100:2376"

# Delete a host
docker-swarm-ctl delete host <host-id>
```

### Swarm Operations

```bash
# Initialize swarm on a host
docker-swarm-ctl swarm init --host <host-id> --advertise-addr 192.168.1.100

# Get swarm info
docker-swarm-ctl swarm info --host <host-id>

# Join a host to swarm
docker-swarm-ctl swarm join --host <host-id> --token <token> --remote-addr <manager-addr>

# Leave swarm
docker-swarm-ctl swarm leave --host <host-id> [--force]
```

### Node Management

```bash
# List nodes
docker-swarm-ctl get nodes --host <host-id>

# Update node availability
docker-swarm-ctl node update <node-id> --host <host-id> --availability drain

# Remove node from swarm
docker-swarm-ctl node rm <node-id> --host <host-id>
```

### Service Management

```bash
# List services
docker-swarm-ctl get services --host <host-id>

# Create a service
docker-swarm-ctl create service --host <host-id> --name nginx --image nginx:alpine --replicas 3

# Scale a service
docker-swarm-ctl scale nginx --host <host-id> --replicas 5

# Delete a service
docker-swarm-ctl delete service nginx --host <host-id>
```

### Container Operations

```bash
# List containers
docker-swarm-ctl get containers --host <host-id>

# View container logs
docker-swarm-ctl logs <container-id> --host <host-id> --follow

# Execute command in container
docker-swarm-ctl exec <container-id> --host <host-id> -- /bin/bash
```

## Output Formats

The CLI supports multiple output formats:

```bash
# Default table format
docker-swarm-ctl get hosts

# JSON output
docker-swarm-ctl get hosts -o json

# YAML output
docker-swarm-ctl get hosts -o yaml

# Wide format (more columns)
docker-swarm-ctl get hosts -o wide
```

## Configuration

The CLI stores its configuration in `~/.docker-swarm-ctl/config.yaml`.

### Context Management

```bash
# Add a new context
docker-swarm-ctl config add-context prod --api-url https://api.example.com

# Switch context
docker-swarm-ctl config use-context prod

# View current context
docker-swarm-ctl config current-context

# Remove a context
docker-swarm-ctl config remove-context old-context
```

### Authentication

The CLI uses JWT tokens for authentication. Tokens are stored in the configuration file per context.

```bash
# Login
docker-swarm-ctl auth login

# Check current user
docker-swarm-ctl auth whoami

# Logout
docker-swarm-ctl auth logout
```

## Building from Source

### Prerequisites

- Go 1.21 or higher
- Make (optional)

### Build Commands

```bash
# Build for current platform
make build

# Build for all platforms
make build-all

# Run tests
make test

# Format code
make fmt

# Run linter
make lint
```

## Development

### Project Structure

```
cli/
├── cmd/           # Command implementations
├── pkg/           # Shared packages
│   ├── client/    # API client
│   ├── config/    # Configuration management
│   └── output/    # Output formatting
├── main.go        # Entry point
├── go.mod         # Go module definition
└── Makefile       # Build automation
```

### Adding New Commands

1. Create a new file in `cmd/` for your command
2. Define the command using cobra
3. Add the command to the root command in `cmd/root.go`
4. Implement the command logic using the API client

## License

MIT License