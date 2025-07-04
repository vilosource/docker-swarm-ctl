#!/bin/bash

# Script to enable Docker TCP endpoint in WSL
# This will configure Docker to listen on both unix socket and TCP

echo "Configuring Docker in WSL to listen on TCP port 2375..."
echo ""
echo "WARNING: This exposes Docker API without authentication!"
echo "         Use only for local development!"
echo ""

# Check if Docker is running
if ! docker version > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Create systemd override directory
echo "Creating systemd override directory..."
sudo mkdir -p /etc/systemd/system/docker.service.d

# Create override configuration
echo "Creating Docker service override..."
sudo tee /etc/systemd/system/docker.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:2375
EOF

echo "Configuration created."
echo ""
echo "Reloading systemd and restarting Docker..."

# Reload systemd and restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# Wait for Docker to start
echo "Waiting for Docker to start..."
sleep 5

# Test the connection
echo ""
echo "Testing Docker TCP connection..."
if curl -s http://localhost:2375/version > /dev/null 2>&1; then
    echo "✓ Docker is now listening on TCP port 2375"
    echo ""
    echo "Version info:"
    curl -s http://localhost:2375/version | jq -r '"\(.Version) (API: \(.ApiVersion))"'
else
    echo "✗ Failed to connect to Docker on TCP port 2375"
    echo ""
    echo "Check Docker status with:"
    echo "  sudo systemctl status docker"
fi

echo ""
echo "Docker is configured to listen on:"
echo "  - Unix socket: /var/run/docker.sock"
echo "  - TCP: tcp://0.0.0.0:2375"