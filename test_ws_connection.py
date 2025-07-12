#!/usr/bin/env python3
"""
Test WebSocket connection via browser console
"""
import requests

# Login to get token
login_response = requests.post("http://localhost/api/v1/auth/login", data={
    "username": "admin@localhost.local",
    "password": "changeme123"
})

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    exit(1)

token = login_response.json()["access_token"]

print("Copy and paste this JavaScript code into your browser console:")
print("=" * 60)
print(f"""
const token = "{token}";
const hostId = "e4e1086d-4533-40cd-8788-069337d04337";
const serviceId = "l8uqcemgt0eh7f3xcar3d2ps2"; // nginx-web service

const wsUrl = `ws://localhost/api/v1/services/${{serviceId}}/logs?host_id=${{hostId}}&tail=100&follow=true&timestamps=false&token=${{token}}`;

console.log("Connecting to:", wsUrl);

const ws = new WebSocket(wsUrl);

ws.onopen = () => {{
    console.log("✅ WebSocket connected successfully!");
}};

ws.onmessage = (event) => {{
    const data = JSON.parse(event.data);
    if (data.type === "log") {{
        console.log("📋 Log:", data.data);
    }} else {{
        console.log("📨 Message:", data);
    }}
}};

ws.onerror = (error) => {{
    console.error("❌ WebSocket error:", error);
}};

ws.onclose = (event) => {{
    console.log("⚠️ WebSocket closed:", event.code, event.reason);
}};

// To close the connection manually:
// ws.close();
""")
print("=" * 60)