# Docker Control Platform - Lab Environment

This directory contains Ansible playbooks and scripts for setting up the lab environment with 4 Docker hosts.

## Lab Hosts
- docker-1.lab.viloforge.com
- docker-2.lab.viloforge.com
- docker-3.lab.viloforge.com
- docker-4.lab.viloforge.com

## Prerequisites
- SSH access as `ansible` user (passwordless via SSH keys)
- Ansible installed on your local machine
- Docker Compose running the main application

## Setup Steps

### 1. Run the complete lab setup
```bash
ansible-playbook setup-lab.yml
```
This single playbook will:
- Install Docker CE on Ubuntu 24.04
- Configure Docker to listen on TCP port 2375 (on eth1 interface)
- Create `dsctl` user with sudo privileges
- Add both `dsctl` and `ansible` users to docker group
- Copy SSH keys for passwordless access
- Verify Docker access for both users

### 2. Configure backend to manage lab hosts

First, ensure the backend is running:
```bash
cd ..
docker-compose up -d
```

Then add the lab hosts to the database:
```bash
docker-compose exec backend python /app/lab/add_lab_hosts.py
```

Or run directly if you have the Python environment:
```bash
cd lab
python add_lab_hosts.py
```

### 3. Test connectivity
```bash
python test_lab_connection.py
```

## Files
- `ansible.cfg` - Ansible configuration
- `inventory` - Host inventory file
- `setup-lab.yml` - Complete lab setup playbook
- `add_lab_hosts.py` - Script to add hosts to backend database
- `test_lab_connection.py` - Script to test Docker connectivity
- `.env.lab` - Example environment configuration for lab

## Notes
- Docker is configured to listen on TCP port 2375 without TLS (suitable for isolated lab environment only)
- The backend uses the multi-host feature to manage all lab hosts
- Each host can be accessed via the web UI after adding to the database