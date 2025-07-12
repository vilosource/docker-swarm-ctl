#!/bin/bash

# Get token
echo "Getting auth token..."
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -d "username=admin@localhost.local&password=changeme123" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

SERVICE_ID="l8uqcemgt0eh7f3xcar3d2ps2"
HOST_ID="e4e1086d-4533-40cd-8788-069337d04337"

echo "Testing WebSocket connection to service logs..."
echo ""

# Test with curl (it will fail but show us the response)
curl -v \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: $(openssl rand -base64 16)" \
  "http://localhost/ws/services/${SERVICE_ID}/logs?host_id=${HOST_ID}&tail=50&follow=true&timestamps=false&token=${TOKEN}" \
  2>&1 | grep -E "< HTTP|< |{" | head -20