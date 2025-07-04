# Docker TCP Configuration for WSL

To configure Docker in WSL to listen on both Unix socket and TCP port 2375, follow these steps:

## Option 1: Using systemd override (Recommended)

1. Create the systemd override directory:
   ```bash
   sudo mkdir -p /etc/systemd/system/docker.service.d
   ```

2. Create the override configuration file:
   ```bash
   sudo nano /etc/systemd/system/docker.service.d/override.conf
   ```

3. Add the following content:
   ```ini
   [Service]
   ExecStart=
   ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:2375
   ```

4. Reload systemd and restart Docker:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart docker
   ```

## Option 2: Edit Docker daemon.json

1. Edit the Docker daemon configuration:
   ```bash
   sudo nano /etc/docker/daemon.json
   ```

2. Add or modify to include:
   ```json
   {
     "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
   }
   ```

3. Restart Docker:
   ```bash
   sudo systemctl restart docker
   ```

## Option 3: Temporary (for testing)

Stop Docker and run it manually with both endpoints:
```bash
sudo systemctl stop docker
sudo dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375
```

## Verify Configuration

Test that Docker is listening on TCP:
```bash
curl http://localhost:2375/version
```

You should see Docker version information in JSON format.

## Security Warning

⚠️ **WARNING**: This configuration exposes Docker API without authentication on port 2375. 
- Only use this for local development
- Do not use in production
- Ensure your firewall blocks external access to port 2375

## For Production

For production environments, use TLS authentication:
```bash
dockerd \
    --tlsverify \
    --tlscacert=ca.pem \
    --tlscert=server-cert.pem \
    --tlskey=server-key.pem \
    -H=0.0.0.0:2376
```