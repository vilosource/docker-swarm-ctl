#!/bin/bash

# Script to enable Docker TCP endpoint for development
# WARNING: This exposes Docker without authentication - use only for local development!

echo "Configuring Docker to listen on TCP port 2375..."
echo ""
echo "This script will:"
echo "1. Create/update Docker daemon configuration"
echo "2. Restart Docker service"
echo ""
echo "NOTE: This configuration is for development only!"
echo "      It exposes Docker API without authentication on tcp://0.0.0.0:2375"
echo ""

# Check if running on WSL
if grep -qi microsoft /proc/version; then
    echo "Detected WSL environment"
    echo ""
    echo "For WSL2, you need to configure Docker Desktop:"
    echo "1. Open Docker Desktop settings"
    echo "2. Go to 'General' tab"
    echo "3. Check 'Expose daemon on tcp://localhost:2375 without TLS'"
    echo "4. Apply & Restart"
    echo ""
    echo "Alternatively, you can edit Docker Desktop settings.json:"
    echo "  Windows: %APPDATA%\Docker\settings.json"
    echo "  Add: \"exposeDockerAPIOnTCP2375\": true"
else
    # For Linux systems
    echo "Creating Docker daemon configuration..."
    
    # Create daemon.json if it doesn't exist
    sudo mkdir -p /etc/docker
    
    # Check if daemon.json exists
    if [ -f /etc/docker/daemon.json ]; then
        echo "Backing up existing daemon.json to daemon.json.bak"
        sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
    fi
    
    # Create new daemon.json with TCP endpoint
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
EOF
    
    echo "Docker daemon configuration updated"
    echo ""
    echo "You need to restart Docker service:"
    echo "  sudo systemctl restart docker"
    echo "or"
    echo "  sudo service docker restart"
fi

echo ""
echo "After configuration, verify with:"
echo "  curl http://localhost:2375/version"