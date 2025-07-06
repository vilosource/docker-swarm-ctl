# Ansible Lab Setup for Docker Hosts

This directory contains Ansible playbooks to configure Docker hosts in the lab environment.

## Network Configuration

The lab uses two network interfaces:
- **eth0 (192.168.100.0/24)**: Internal lab network for Docker API communication
- **eth1**: External network for internet access and management

Docker is configured to listen on:
- **Unix socket** (`/var/run/docker.sock`): For local access by users on the host
- **TCP on eth0** (`192.168.100.x:2375`): For remote API access from the control platform

## Inventory

The inventory file defines the lab hosts:
```
docker-1.lab.viloforge.com - 192.168.100.11
docker-2.lab.viloforge.com - 192.168.100.12
docker-3.lab.viloforge.com - 192.168.100.13
docker-4.lab.viloforge.com - 192.168.100.14
```

## Playbooks

### 1. setup-lab.yml
Complete lab setup including Docker installation and user configuration.
```bash
ansible-playbook -i inventory setup-lab.yml
```

### 2. configure-docker-simple.yml
Configure Docker to listen on eth0 (192.168.100.x) without TLS (for testing).
```bash
ansible-playbook -i inventory configure-docker-simple.yml
```

### 3. configure-docker-tls.yml
Configure Docker with TLS for secure API access (recommended for production-like testing).
```bash
ansible-playbook -i inventory configure-docker-tls.yml
```

## Quick Start

1. Ensure you can SSH to the lab hosts as the `ansible` user
2. Run the simple configuration for testing:
   ```bash
   ansible-playbook -i inventory configure-docker-simple.yml
   ```

3. Verify Docker is accessible:
   ```bash
   curl http://192.168.100.11:2375/version
   ```

## Connecting from Docker Control Platform

After running the playbooks, you can add the hosts to the Docker Control Platform:

1. Run the add_lab_hosts.py script:
   ```bash
   cd ..
   python lab/add_lab_hosts.py
   ```

2. The hosts will be accessible at:
   - tcp://192.168.100.11:2375
   - tcp://192.168.100.12:2375
   - tcp://192.168.100.13:2375
   - tcp://192.168.100.14:2375

## Security Notes

- The simple configuration (port 2375) has **no authentication** - use only in isolated lab environments
- For production-like testing, use the TLS configuration (port 2376)
- The eth0 interface should be on an isolated network segment

## Troubleshooting

1. Check Docker is listening on both socket and TCP:
   ```bash
   sudo ss -tlnp | grep docker
   # Should show both unix socket and tcp:2375
   ```

2. Test local socket access:
   ```bash
   docker ps  # Should work without setting DOCKER_HOST
   ```

3. Test TCP connectivity from the control platform host:
   ```bash
   nc -zv 192.168.100.11 2375
   curl http://192.168.100.11:2375/version
   ```

4. Check Docker logs:
   ```bash
   sudo journalctl -u docker -f
   ```