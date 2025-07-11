import React from 'react'
import { WizardStepProps } from '../WizardModal'
import { HostType } from '@/types'

export const ConnectionDetailsStep: React.FC<WizardStepProps> = ({
  state,
  onStateChange,
  error
}) => {
  return (
    <div>
      <p className="text-muted mb-3">
        Enter the connection details for your Docker host.
      </p>

      <div className="alert alert-info">
        <i className="mdi mdi-information-outline me-1"></i>
        The SSH URL should be in the format: ssh://[user@]hostname[:port]
        <br />
        Example: ssh://root@docker-host.example.com or ssh://admin@192.168.1.100:2222
      </div>

      <div className="row g-3">
        <div className="col-12">
          <label className="form-label">Connection Name *</label>
          <input
            type="text"
            className="form-control"
            value={state.connection_name || ''}
            onChange={(e) => onStateChange({ connection_name: e.target.value })}
            required
            placeholder="e.g., production-docker-1"
          />
          <small className="text-muted">A friendly name to identify this host</small>
        </div>

        <div className="col-12">
          <label className="form-label">SSH URL *</label>
          <input
            type="text"
            className="form-control"
            value={state.host_url || ''}
            onChange={(e) => onStateChange({ host_url: e.target.value })}
            required
            placeholder="ssh://root@hostname"
          />
          <small className="text-muted">SSH connection URL for the Docker host</small>
        </div>

        <div className="col-md-6">
          <label className="form-label">SSH Port</label>
          <input
            type="number"
            className="form-control"
            value={state.ssh_port || 22}
            onChange={(e) => onStateChange({ ssh_port: parseInt(e.target.value) || 22 })}
            min={1}
            max={65535}
          />
          <small className="text-muted">Default: 22</small>
        </div>

        <div className="col-md-6">
          <label className="form-label">Host Type</label>
          <select
            className="form-select"
            value={state.host_type || 'standalone'}
            onChange={(e) => onStateChange({ host_type: e.target.value as HostType })}
          >
            <option value="standalone">Standalone Docker Host</option>
            <option value="swarm_manager">Docker Swarm Manager</option>
            <option value="swarm_worker">Docker Swarm Worker</option>
          </select>
        </div>

        <div className="col-12">
          <label className="form-label">Display Name</label>
          <input
            type="text"
            className="form-control"
            value={state.display_name || ''}
            onChange={(e) => onStateChange({ display_name: e.target.value })}
            placeholder="Optional: Display name for UI"
          />
          <small className="text-muted">Display name for UI (defaults to connection name)</small>
        </div>

        <div className="col-12">
          <label className="form-label">Description</label>
          <textarea
            className="form-control"
            value={state.description || ''}
            onChange={(e) => onStateChange({ description: e.target.value })}
            rows={3}
            placeholder="Optional: Description of this host"
          />
        </div>
      </div>
    </div>
  )
}