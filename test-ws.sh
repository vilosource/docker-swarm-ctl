#!/bin/bash

echo "Docker WebSocket Test Script"
echo "============================"

# Get auth token
echo -n "Enter username (default: admin@localhost): "
read USERNAME
USERNAME=${USERNAME:-admin@localhost}

echo -n "Enter password: "
read -s PASSWORD
echo

echo -e "\n1. Getting authentication token..."
TOKEN_RESPONSE=$(curl -s -X POST http://localhost/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Error: Failed to get token"
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi

echo "✓ Token obtained successfully"
echo "Token: ${ACCESS_TOKEN:0:20}..."

# Test API connection
echo -e "\n2. Testing API connection..."
USER_RESPONSE=$(curl -s -X GET http://localhost/api/v1/users/me \
  -H "Authorization: Bearer $ACCESS_TOKEN")

USERNAME_FROM_API=$(echo $USER_RESPONSE | grep -o '"username":"[^"]*' | grep -o '[^"]*$')
if [ -n "$USERNAME_FROM_API" ]; then
  echo "✓ API connection successful. User: $USERNAME_FROM_API"
else
  echo "Error: API test failed"
  echo "Response: $USER_RESPONSE"
  exit 1
fi

# Get container list
echo -e "\n3. Getting container list..."
CONTAINERS=$(docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}" | tail -n +2)

if [ -z "$CONTAINERS" ]; then
  echo "No running containers found. Starting a test container..."
  docker run -d --name test-nginx nginx:alpine
  sleep 2
  CONTAINERS=$(docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}" | tail -n +2)
fi

echo "Running containers:"
echo "$CONTAINERS"

echo -e "\n4. Select a container ID from above and paste it here:"
read CONTAINER_ID

# Construct WebSocket URL
WS_URL="ws://localhost/ws/containers/${CONTAINER_ID}/logs?token=${ACCESS_TOKEN}&follow=true&tail=50&timestamps=true"

echo -e "\n5. WebSocket URL constructed:"
echo "$WS_URL"

echo -e "\n6. Testing WebSocket connection with wscat..."
echo "If wscat is not installed, run: npm install -g wscat"
echo -e "\nPress Ctrl+C to stop\n"

# Test with wscat if available
if command -v wscat &> /dev/null; then
  wscat -c "$WS_URL"
else
  echo "wscat not found. Install it with: npm install -g wscat"
  echo ""
  echo "Alternatively, open this URL in your browser's console:"
  echo "new WebSocket('$WS_URL')"
  echo ""
  echo "Or use the test page: http://localhost/test-websocket.html"
  echo "Token: $ACCESS_TOKEN"
  echo "Container ID: $CONTAINER_ID"
fi