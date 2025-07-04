# Traefik WebSocket Load Balancing Guide for Docker Control Platform

## Table of Contents
1. [Why Traefik for Docker Applications](#why-traefik-for-docker-applications)
2. [Complete Traefik Configuration](#complete-traefik-configuration)
3. [Docker Compose Setup](#docker-compose-setup)
4. [Traefik vs Nginx Comparison](#traefik-vs-nginx-comparison)
5. [Advanced Traefik Features](#advanced-traefik-features)
6. [Monitoring and Debugging](#monitoring-and-debugging)

## Why Traefik for Docker Applications

Traefik is particularly well-suited for Docker-based applications like the Docker Control Platform for several key reasons:

### 1. Native Docker Integration
- **Service Discovery**: Automatically discovers containers via Docker labels
- **Dynamic Configuration**: Updates routing without restarts when containers scale
- **Docker Swarm Support**: Native integration with Docker Swarm mode
- **Container Health Checks**: Automatically removes unhealthy containers from load balancing

### 2. WebSocket Excellence
- **Built-in WebSocket Support**: No special configuration required
- **Protocol Detection**: Automatically detects and handles WebSocket upgrades
- **Connection Persistence**: Maintains long-lived WebSocket connections
- **Sticky Sessions**: Multiple methods for session affinity

### 3. Modern Architecture
- **Edge Router**: Designed as a modern edge router with cloud-native principles
- **Middleware System**: Extensible middleware for authentication, rate limiting, etc.
- **Multiple Providers**: Supports Docker, Kubernetes, Consul, etc.
- **Let's Encrypt Integration**: Automatic HTTPS with certificate management

## Complete Traefik Configuration

### Static Configuration (traefik.yml)

```yaml
# /etc/traefik/traefik.yml
global:
  checkNewVersion: true
  sendAnonymousUsage: false

api:
  dashboard: true
  debug: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: docker-control-net
    watch: true

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

log:
  level: INFO
  filePath: /var/log/traefik/traefik.log
  format: json

accessLog:
  filePath: /var/log/traefik/access.log
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: keep

metrics:
  prometheus:
    addEntryPointsLabels: true
    addServicesLabels: true
    entryPoint: metrics

ping:
  entryPoint: ping

serversTransport:
  insecureSkipVerify: true
```

### Dynamic Configuration via Docker Labels

```yaml
# Backend service with WebSocket support
backend:
  image: docker-control-backend:latest
  labels:
    # Enable Traefik
    - "traefik.enable=true"
    
    # HTTP Router
    - "traefik.http.routers.backend.rule=Host(`api.docker-control.local`) && PathPrefix(`/api`)"
    - "traefik.http.routers.backend.entrypoints=websecure"
    - "traefik.http.routers.backend.tls=true"
    - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
    
    # WebSocket Router
    - "traefik.http.routers.backend-ws.rule=Host(`api.docker-control.local`) && PathPrefix(`/ws`)"
    - "traefik.http.routers.backend-ws.entrypoints=websecure"
    - "traefik.http.routers.backend-ws.tls=true"
    
    # Service Configuration with Sticky Sessions
    - "traefik.http.services.backend.loadbalancer.server.port=8000"
    - "traefik.http.services.backend.loadbalancer.sticky.cookie=true"
    - "traefik.http.services.backend.loadbalancer.sticky.cookie.name=backend_session"
    - "traefik.http.services.backend.loadbalancer.sticky.cookie.httponly=true"
    - "traefik.http.services.backend.loadbalancer.sticky.cookie.secure=true"
    - "traefik.http.services.backend.loadbalancer.sticky.cookie.samesite=strict"
    
    # Health Check
    - "traefik.http.services.backend.loadbalancer.healthcheck.path=/api/health"
    - "traefik.http.services.backend.loadbalancer.healthcheck.interval=10s"
    - "traefik.http.services.backend.loadbalancer.healthcheck.timeout=5s"
    
    # Middleware
    - "traefik.http.middlewares.backend-ratelimit.ratelimit.average=100"
    - "traefik.http.middlewares.backend-ratelimit.ratelimit.burst=200"
    - "traefik.http.middlewares.backend-compress.compress=true"
    - "traefik.http.middlewares.backend-headers.headers.customrequestheaders.X-Real-IP=$${CLIENT_IP}"
    - "traefik.http.routers.backend.middlewares=backend-ratelimit,backend-compress,backend-headers"
```

## Docker Compose Setup

### Complete docker-compose.yml with Traefik and Multiple Backend Instances

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik/traefik.yml:/traefik.yml:ro
      - ./traefik/config:/config:ro
      - ./traefik/certs:/letsencrypt
      - ./traefik/logs:/var/log/traefik
    networks:
      - docker-control-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.entrypoints=websecure"
      - "traefik.http.routers.traefik.rule=Host(`traefik.docker-control.local`)"
      - "traefik.http.routers.traefik.tls=true"
      - "traefik.http.routers.traefik.service=api@internal"
      - "traefik.http.routers.traefik.middlewares=traefik-auth"
      - "traefik.http.middlewares.traefik-auth.basicauth.users=admin:$$2y$$10$$..."

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: docker_control
      POSTGRES_USER: docker_control
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - docker-control-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U docker_control"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - docker-control-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend Instance 1
  backend-1:
    image: docker-control-backend:latest
    restart: unless-stopped
    environment:
      - INSTANCE_ID=backend-1
      - DATABASE_URL=postgresql://docker_control:${DB_PASSWORD}@postgres/docker_control
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - docker-control-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.docker-control.local`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls=true"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
      - "traefik.http.services.backend.loadbalancer.sticky.cookie=true"
      - "traefik.http.services.backend.loadbalancer.sticky.cookie.name=backend_session"
      - "traefik.http.services.backend.loadbalancer.healthcheck.path=/api/health"

  # Backend Instance 2
  backend-2:
    image: docker-control-backend:latest
    restart: unless-stopped
    environment:
      - INSTANCE_ID=backend-2
      - DATABASE_URL=postgresql://docker_control:${DB_PASSWORD}@postgres/docker_control
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - docker-control-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.docker-control.local`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls=true"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"

  # Backend Instance 3
  backend-3:
    image: docker-control-backend:latest
    restart: unless-stopped
    environment:
      - INSTANCE_ID=backend-3
      - DATABASE_URL=postgresql://docker_control:${DB_PASSWORD}@postgres/docker_control
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - docker-control-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.docker-control.local`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls=true"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"

  frontend:
    image: docker-control-frontend:latest
    restart: unless-stopped
    environment:
      - VITE_API_URL=https://api.docker-control.local
      - VITE_WS_URL=wss://api.docker-control.local
    volumes:
      - ./frontend:/app
    networks:
      - docker-control-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`docker-control.local`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls=true"
      - "traefik.http.services.frontend.loadbalancer.server.port=3000"

networks:
  docker-control-net:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### Advanced Traefik Configuration for WebSockets

```yaml
# traefik/config/websocket.yml
http:
  middlewares:
    websocket-headers:
      headers:
        customRequestHeaders:
          X-Forwarded-Proto: "https"
          Connection: "upgrade"
        customResponseHeaders:
          X-Content-Type-Options: "nosniff"
          X-Frame-Options: "SAMEORIGIN"
    
    websocket-ratelimit:
      rateLimit:
        average: 10
        burst: 20
        period: 1m
        sourceCriterion:
          ipStrategy:
            depth: 1
    
    websocket-circuit-breaker:
      circuitBreaker:
        expression: "ResponseCodeRatio(500, 600, 0, 600) > 0.50"
        checkPeriod: 10s
        fallbackDuration: 10s
        recoveryDuration: 10s

  routers:
    websocket-router:
      rule: "PathPrefix(`/ws`)"
      service: backend-websocket
      middlewares:
        - websocket-headers
        - websocket-ratelimit
        - websocket-circuit-breaker
      tls: true

  services:
    backend-websocket:
      loadBalancer:
        sticky:
          cookie:
            name: ws_affinity
            secure: true
            httpOnly: true
            sameSite: strict
        servers:
          - url: "http://backend-1:8000"
          - url: "http://backend-2:8000"
          - url: "http://backend-3:8000"
        healthCheck:
          path: /api/health
          interval: 10s
          timeout: 5s
          scheme: http
```

## Traefik vs Nginx Comparison

### Traefik Advantages

| Feature | Traefik | Nginx |
|---------|---------|-------|
| **Docker Integration** | Native with auto-discovery | Requires manual configuration |
| **Dynamic Configuration** | No restart needed | Requires reload/restart |
| **Service Discovery** | Automatic via labels | Manual upstream definition |
| **WebSocket Support** | Built-in, zero config | Requires explicit configuration |
| **HTTPS/TLS** | Automatic with Let's Encrypt | Manual certificate management |
| **Load Balancing** | Multiple algorithms built-in | Basic round-robin by default |
| **Health Checks** | Native with multiple types | Requires Nginx Plus or custom |
| **Metrics** | Prometheus/StatsD built-in | Requires additional modules |
| **Circuit Breaker** | Built-in middleware | Not available |
| **Rate Limiting** | Built-in middleware | Requires additional modules |

### Configuration Comparison

#### Nginx WebSocket Configuration
```nginx
upstream backend {
    ip_hash;
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
    server backend-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
```

#### Traefik WebSocket Configuration
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.ws.rule=PathPrefix(`/ws`)"
  - "traefik.http.services.backend.loadbalancer.sticky.cookie=true"
```

### Performance Comparison

| Metric | Traefik | Nginx |
|--------|---------|-------|
| **Request Latency** | ~1-2ms overhead | <1ms overhead |
| **Throughput** | ~50k req/s | ~100k req/s |
| **Memory Usage** | ~100-200MB | ~50-100MB |
| **CPU Usage** | Higher due to Go runtime | Lower, C-based |
| **WebSocket Connections** | 100k+ concurrent | 100k+ concurrent |
| **Configuration Reload** | Zero downtime | Graceful reload |

## Advanced Traefik Features

### 1. Canary Deployments
```yaml
http:
  services:
    backend-canary:
      weighted:
        services:
          - name: backend-stable
            weight: 90
          - name: backend-canary
            weight: 10
        sticky:
          cookie:
            name: canary_session
```

### 2. Request Mirroring
```yaml
http:
  services:
    backend-mirror:
      mirroring:
        service: backend-main
        mirrors:
          - name: backend-test
            percent: 10
```

### 3. Retry Mechanism
```yaml
http:
  middlewares:
    retry-middleware:
      retry:
        attempts: 4
        initialInterval: 100ms
        multiplier: 2
        maxInterval: 1s
```

### 4. Custom Headers and Authentication
```yaml
http:
  middlewares:
    auth-headers:
      headers:
        customRequestHeaders:
          X-Auth-Request-User: "${user}"
          X-Auth-Request-Email: "${email}"
    
    forward-auth:
      forwardAuth:
        address: "http://auth-service:8080/verify"
        authResponseHeaders:
          - "X-Auth-User"
          - "X-Auth-Role"
```

### 5. WebSocket-Specific Middleware Chain
```yaml
labels:
  - "traefik.http.routers.ws.middlewares=websocket-auth,websocket-compress,websocket-ratelimit"
  - "traefik.http.middlewares.websocket-auth.forwardauth.address=http://auth:8080/ws/verify"
  - "traefik.http.middlewares.websocket-compress.compress=true"
  - "traefik.http.middlewares.websocket-ratelimit.ratelimit.average=100"
```

## Monitoring and Debugging

### 1. Enable Debug Logging
```yaml
# traefik.yml
log:
  level: DEBUG
  format: json

accessLog:
  filePath: /var/log/traefik/access.log
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: keep
  filters:
    statusCodes:
      - "200-299"
      - "400-499"
      - "500-599"
```

### 2. Prometheus Metrics
```yaml
metrics:
  prometheus:
    buckets:
      - 0.1
      - 0.3
      - 1.2
      - 5.0
    addEntryPointsLabels: true
    addRoutersLabels: true
    addServicesLabels: true
    entryPoint: metrics
```

### 3. WebSocket Connection Monitoring
```bash
# Monitor WebSocket connections
curl http://localhost:8080/api/overview | jq '.http.services."backend@docker".serverStatus'

# Check sticky session distribution
for i in {1..10}; do
  curl -s -H "Cookie: backend_session=test123" https://api.docker-control.local/api/instance
done | sort | uniq -c

# Monitor WebSocket upgrade success rate
grep -E "Upgrade.*websocket" /var/log/traefik/access.log | wc -l
```

### 4. Traefik Dashboard Configuration
```yaml
api:
  dashboard: true
  debug: true
  
labels:
  - "traefik.http.routers.dashboard.rule=Host(`traefik.docker-control.local`)"
  - "traefik.http.routers.dashboard.service=api@internal"
  - "traefik.http.routers.dashboard.middlewares=dashboard-auth"
  - "traefik.http.middlewares.dashboard-auth.basicauth.users=admin:$$2y$$10$$..."
```

### 5. Custom WebSocket Metrics
```go
// Backend code to expose WebSocket metrics
type WebSocketMetrics struct {
    ActiveConnections   int64     `json:"active_connections"`
    TotalConnections    int64     `json:"total_connections"`
    MessagesReceived    int64     `json:"messages_received"`
    MessagesSent        int64     `json:"messages_sent"`
    ConnectionDuration  []float64 `json:"connection_duration_seconds"`
    LastError          string    `json:"last_error"`
    LastErrorTime      time.Time `json:"last_error_time"`
}
```

### 6. Debugging Commands
```bash
# Check Traefik configuration
docker exec traefik traefik validate

# View real-time logs
docker logs -f traefik 2>&1 | jq -r 'select(.level=="error" or .msg | contains("websocket"))'

# Test WebSocket connection
websocat -v wss://api.docker-control.local/ws/echo

# Monitor sticky session cookies
tcpdump -i any -A -s 0 'tcp port 443 and (tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x47455420)'

# Check backend health
for backend in backend-1 backend-2 backend-3; do
  echo -n "$backend: "
  docker exec $backend curl -s http://localhost:8000/api/health | jq -r '.status'
done
```

### 7. Grafana Dashboard for WebSocket Monitoring
```json
{
  "dashboard": {
    "title": "Traefik WebSocket Monitoring",
    "panels": [
      {
        "title": "Active WebSocket Connections",
        "targets": [{
          "expr": "traefik_service_open_connections{service=~\".*websocket.*\"}"
        }]
      },
      {
        "title": "WebSocket Request Rate",
        "targets": [{
          "expr": "rate(traefik_service_requests_total{service=~\".*websocket.*\"}[5m])"
        }]
      },
      {
        "title": "WebSocket Error Rate",
        "targets": [{
          "expr": "rate(traefik_service_requests_total{service=~\".*websocket.*\",code!~\"2..\"}[5m])"
        }]
      },
      {
        "title": "Sticky Session Distribution",
        "targets": [{
          "expr": "traefik_service_server_up{service=\"backend@docker\"}"
        }]
      }
    ]
  }
}
```

## Best Practices

1. **Use Dedicated WebSocket Service**: Separate WebSocket traffic from regular HTTP
2. **Enable Compression**: Use Traefik's compress middleware for WebSocket frames
3. **Set Appropriate Timeouts**: Configure longer timeouts for WebSocket connections
4. **Monitor Connection Limits**: Set and monitor max connection limits
5. **Use Health Checks**: Implement WebSocket-specific health endpoints
6. **Enable Access Logs**: Log WebSocket upgrades and connection duration
7. **Implement Circuit Breakers**: Protect against cascading failures
8. **Use Sticky Sessions**: Ensure WebSocket reconnects hit the same backend

## Conclusion

Traefik provides a modern, Docker-native solution for WebSocket load balancing that excels in:
- Automatic service discovery and configuration
- Built-in WebSocket support with zero configuration
- Advanced features like circuit breakers and canary deployments
- Comprehensive monitoring and debugging capabilities

While Nginx offers better raw performance, Traefik's operational benefits and Docker integration make it the superior choice for containerized applications like the Docker Control Platform.