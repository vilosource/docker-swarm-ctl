#!/bin/bash

# First get the token
echo "Getting auth token..."
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -d "username=admin@localhost.local&password=changeme123" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token"
  exit 1
fi

echo "Token obtained successfully"

# Get the nginx service ID
echo "Finding nginx service..."
SERVICE_INFO=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/services/?host_id=e4e1086d-4533-40cd-8788-069337d04337" \
  | grep -o '"ID":"[^"]*","name":"nginx-web"' | cut -d'"' -f4)

if [ -z "$SERVICE_INFO" ]; then
  echo "Nginx service not found, creating it..."
  curl -s -X POST "http://localhost/api/v1/services/?host_id=e4e1086d-4533-40cd-8788-069337d04337" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "nginx-web",
      "image": "nginx:alpine",
      "replicas": 2,
      "ports": [{
        "Protocol": "tcp",
        "TargetPort": 80,
        "PublishedPort": 9091,
        "PublishMode": "ingress"
      }]
    }'
  
  # Get the service ID again
  SERVICE_INFO=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "http://localhost/api/v1/services/?host_id=e4e1086d-4533-40cd-8788-069337d04337" \
    | grep -o '"ID":"[^"]*","name":"nginx-web"' | cut -d'"' -f4)
fi

echo "Service ID: $SERVICE_INFO"

# Generate some traffic to nginx to create logs
echo "Generating traffic to nginx..."
for i in {1..5}; do
  curl -s http://localhost:9091 > /dev/null
  echo "Request $i sent"
  sleep 1
done

echo ""
echo "Now you can test the WebSocket connection with this command:"
echo ""
echo "wscat -c \"ws://localhost/api/v1/services/$SERVICE_INFO/logs?host_id=e4e1086d-4533-40cd-8788-069337d04337&tail=50&follow=true&timestamps=false&token=$TOKEN\""
echo ""
echo "Or use this JavaScript in the browser console:"
echo ""
cat << EOF
const ws = new WebSocket("ws://localhost/api/v1/services/$SERVICE_INFO/logs?host_id=e4e1086d-4533-40cd-8788-069337d04337&tail=50&follow=true&timestamps=false&token=$TOKEN");
ws.onopen = () => console.log("Connected!");
ws.onmessage = (e) => console.log("Log:", JSON.parse(e.data));
ws.onerror = (e) => console.error("Error:", e);
ws.onclose = (e) => console.log("Closed:", e.code, e.reason);
EOF