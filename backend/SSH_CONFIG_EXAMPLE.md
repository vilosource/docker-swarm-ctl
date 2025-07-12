# SSH Configuration Examples

This document shows how to use SSH connections with Docker Swarm Control Platform.

## Option 1: Using System SSH Configuration (Recommended)

If you already have SSH configured on your system, you can use your existing SSH setup without providing any credentials.

### Prerequisites
1. SSH keys configured in `~/.ssh/`
2. SSH agent running (optional but recommended)
3. Host configuration in `~/.ssh/config` (optional)

### Example SSH Config (`~/.ssh/config`)
```
Host docker-prod
    HostName prod-server.example.com
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/id_rsa_prod
    
Host docker-staging
    HostName staging.internal
    User deploy
    ProxyJump bastion.example.com
    IdentityFile ~/.ssh/staging_key
```

### Creating Host in Docker Control Platform

1. **Simple setup (using SSH config alias)**:
   - Host URL: `ssh://docker-prod`
   - No credentials needed!

2. **Direct connection (using SSH agent or default keys)**:
   - Host URL: `ssh://ubuntu@prod-server.example.com`
   - No credentials needed if SSH keys are in `~/.ssh/`

3. **With specific user**:
   - Host URL: `ssh://deploy@10.0.1.50:2222`
   - Will use SSH agent or identity files from `~/.ssh/`

## Option 2: Explicit Credentials

If you need to provide credentials explicitly:

### With Private Key
```json
{
  "credentials": [
    {
      "credential_type": "ssh_private_key",
      "credential_value": "-----BEGIN RSA PRIVATE KEY-----\n..."
    },
    {
      "credential_type": "ssh_private_key_passphrase",
      "credential_value": "key_passphrase_here"
    }
  ]
}
```

### With Password
```json
{
  "credentials": [
    {
      "credential_type": "ssh_password",
      "credential_value": "password_here"
    }
  ]
}
```

## Option 3: Mixed Configuration

You can combine system SSH config with explicit settings:

### Disable SSH Config Usage
```json
{
  "credentials": [
    {
      "credential_type": "use_ssh_config",
      "credential_value": "false"
    },
    {
      "credential_type": "ssh_private_key",
      "credential_value": "-----BEGIN RSA PRIVATE KEY-----\n..."
    }
  ]
}
```

## Authentication Priority

The SSH connection will try authentication methods in this order:
1. Explicit private key (if provided)
2. Explicit password (if provided)
3. SSH agent keys
4. Identity files from SSH config
5. Default identity files (`~/.ssh/id_rsa`, etc.)

## Security Notes

1. **SSH Agent**: If you have an SSH agent running, it will be used automatically
2. **Known Hosts**: System's `~/.ssh/known_hosts` is used by default
3. **ProxyCommand/ProxyJump**: Fully supported from SSH config
4. **Host Aliases**: You can use aliases from your SSH config

## Minimal Setup Example

For the easiest setup:
1. Ensure your SSH key is in `~/.ssh/` and loaded in SSH agent
2. Create a host with URL: `ssh://your-server.com`
3. That's it! No credentials needed.

## Troubleshooting

If connection fails:
1. Test with regular SSH first: `ssh your-server.com`
2. Check if Docker is accessible: `ssh your-server.com docker version`
3. Ensure the SSH user has Docker permissions
4. Check circuit breaker status if connection was previously failing