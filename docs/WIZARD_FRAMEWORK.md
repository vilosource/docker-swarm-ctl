# Wizard Framework Documentation

## Overview

The Docker Control Platform includes a comprehensive wizard framework designed to guide users through complex multi-step configuration processes. This framework provides a consistent, resumable, and user-friendly experience for tasks like setting up SSH hosts, initializing Docker Swarm clusters, and deploying services.

## Architecture

### Core Components

1. **WizardInstance Model**: Stores wizard state and metadata in PostgreSQL
2. **WizardService**: Business logic for wizard operations
3. **Wizard Type Implementations**: Specific logic for each wizard type
4. **API Endpoints**: RESTful API for wizard operations
5. **Frontend Components**: Reusable UI components for wizard display

### Database Schema

```sql
CREATE TABLE wizard_instances (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    wizard_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    resource_id UUID,
    resource_type VARCHAR(50),
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress',
    state JSONB NOT NULL DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### Wizard Types

Currently implemented:
- `ssh_host_setup`: SSH-based Docker host configuration

Planned:
- `swarm_init`: Initialize a new Docker Swarm cluster
- `swarm_join`: Join an existing Swarm cluster
- `service_deployment`: Deploy a new service to Swarm

## SSH Host Setup Wizard

### Steps

1. **Connection Details**
   - Host URL (format: `ssh://user@host:port`)
   - Display name and description
   - Host type (standalone, swarm_manager, swarm_worker)
   - SSH configuration options

2. **Authentication**
   - Method selection: new key, existing key, or password
   - ED25519 key generation with custom comments
   - Private key import with passphrase support
   - Password authentication option

3. **SSH Connection Test**
   - Verify SSH connectivity
   - Gather system information
   - Display connection status and errors

4. **Docker API Test**
   - Verify Docker daemon accessibility
   - Check Docker version and configuration
   - Determine if host is part of a Swarm

5. **Confirmation**
   - Review configuration
   - Add tags for organization
   - Set as default host option
   - Create host with `setup_pending` status

### Security Features

- All credentials encrypted before storage
- SSH keys generated using cryptography library
- Support for SSH key passphrases
- No plaintext passwords stored
- Audit logging for all wizard operations

## API Usage

### Starting a Wizard

```bash
POST /api/v1/wizards/start
{
    "wizard_type": "ssh_host_setup",
    "initial_state": {
        "host_url": "ssh://admin@server.example.com"
    }
}
```

### Updating Step Data

```bash
PUT /api/v1/wizards/{wizard_id}/step
{
    "step_data": {
        "connection_name": "Production Server",
        "display_name": "Main Production Host",
        "ssh_port": 22
    }
}
```

### Navigation

```bash
POST /api/v1/wizards/{wizard_id}/next
POST /api/v1/wizards/{wizard_id}/previous
```

### Testing

```bash
POST /api/v1/wizards/{wizard_id}/test
{
    "test_type": "ssh_connection"
}
```

### Completion

```bash
POST /api/v1/wizards/{wizard_id}/complete
```

### SSH Key Generation

```bash
POST /api/v1/wizards/generate-ssh-key?comment=user@host
```

Response:
```json
{
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----...",
    "public_key": "ssh-ed25519 AAAA... user@host",
    "key_type": "ed25519",
    "comment": "user@host"
}
```

## Frontend Integration

### Using the Wizard Components

```typescript
import { SSHHostWizard } from '@/components/wizards/SSHHostWizard';

function HostsPage() {
    const [showWizard, setShowWizard] = useState(false);
    
    return (
        <>
            <Button onClick={() => setShowWizard(true)}>
                Add SSH Host
            </Button>
            
            {showWizard && (
                <SSHHostWizard
                    onComplete={(host) => {
                        console.log('Host created:', host);
                        setShowWizard(false);
                    }}
                    onCancel={() => setShowWizard(false)}
                />
            )}
        </>
    );
}
```

### Wizard State Management

The wizard maintains its state in the backend, allowing users to:
- Close the wizard and resume later
- Navigate between steps without losing data
- Have multiple wizards in progress
- Resume wizards after browser refresh

## Implementation Notes

### JSONB Field Updates

When updating JSONB fields in SQLAlchemy, always use reassignment:

```python
# Correct - triggers change detection
new_state = dict(wizard.state)
new_state.update(step_data)
wizard.state = new_state

# Incorrect - won't persist
wizard.state.update(step_data)
```

### Error Handling

The wizard framework provides comprehensive error handling:
- Validation errors show inline in the UI
- Connection errors provide detailed feedback
- Network timeouts are handled gracefully
- All errors are logged for debugging

### Testing Wizards

```python
# Example test script
import requests

# Login
response = requests.post("http://localhost:8000/api/v1/auth/login", 
    data={"username": "admin@localhost", "password": "changeme123"})
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Start wizard
response = requests.post("http://localhost:8000/api/v1/wizards/start",
    headers=headers,
    json={"wizard_type": "ssh_host_setup"})
wizard_id = response.json()["id"]

# Update steps and complete...
```

## Future Enhancements

1. **Wizard Templates**: Pre-configured wizards for common scenarios
2. **Bulk Operations**: Apply wizard to multiple resources
3. **Conditional Steps**: Dynamic step flow based on user choices
4. **Import/Export**: Save and share wizard configurations
5. **Validation Webhooks**: Custom validation logic via external APIs
6. **Progress Persistence**: Save partial progress in browser storage
7. **Wizard Analytics**: Track completion rates and common errors