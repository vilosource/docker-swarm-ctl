import React from 'react'
import { WizardStepProps } from '../WizardModal'

export const ConfirmationStep: React.FC<WizardStepProps> = ({
  state,
  onStateChange,
  error
}) => {
  // Parse tags from comma-separated string
  const handleTagsChange = (value: string) => {
    const tags = value.split(',').map(tag => tag.trim()).filter(tag => tag)
    onStateChange({ tags_string: value, tags })
  }

  return (
    <div>
      <p className="text-muted mb-3">
        Review the configuration and confirm to create the host.
      </p>

      <div className="alert alert-success mb-4">
        <i className="mdi mdi-check-circle-outline me-1"></i>
        All tests passed! Your host is ready to be added to the platform.
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <h6 className="card-title">Host Configuration Summary</h6>
          <dl className="row mb-0">
            <dt className="col-sm-3">Connection Name</dt>
            <dd className="col-sm-9">{state.connection_name}</dd>
            
            <dt className="col-sm-3">Host URL</dt>
            <dd className="col-sm-9">{state.host_url}</dd>
            
            <dt className="col-sm-3">Host Type</dt>
            <dd className="col-sm-9">
              <span className={`badge ${
                state.host_type === 'swarm_manager' ? 'bg-primary' : 
                state.host_type === 'swarm_worker' ? 'bg-info' : 'bg-secondary'
              }`}>
                {state.host_type?.replace('_', ' ').toUpperCase() || 'STANDALONE'}
              </span>
            </dd>
            
            <dt className="col-sm-3">Authentication</dt>
            <dd className="col-sm-9">
              {state.auth_method === 'new_key' ? 'Generated SSH Key' :
               state.auth_method === 'existing_key' ? 'Existing SSH Key' :
               'Password Authentication'}
            </dd>
            
            {state.docker_info && (
              <>
                <dt className="col-sm-3">Docker Version</dt>
                <dd className="col-sm-9">{state.docker_info.version}</dd>
              </>
            )}
          </dl>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-12">
          <div className="form-check">
            <input
              type="checkbox"
              className="form-check-input"
              id="isDefault"
              checked={state.is_default || false}
              onChange={(e) => onStateChange({ is_default: e.target.checked })}
            />
            <label className="form-check-label" htmlFor="isDefault">
              Set as default host
            </label>
          </div>
        </div>

        <div className="col-12">
          <label className="form-label">Tags</label>
          <input
            type="text"
            className="form-control"
            value={state.tags_string || ''}
            onChange={(e) => handleTagsChange(e.target.value)}
            placeholder="production, web-server"
          />
          <small className="text-muted">Optional: Comma-separated tags (e.g., production, web-server, us-east)</small>
        </div>

        {state.tags && state.tags.length > 0 && (
          <div className="col-12">
            <div className="d-flex gap-2 flex-wrap">
              {state.tags.map((tag: string, index: number) => (
                <span key={index} className="badge bg-light text-dark">
                  <i className="mdi mdi-tag-outline me-1"></i>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {state.auth_method === 'new_key' && state.public_key && (
        <div className="alert alert-info mt-4">
          <i className="mdi mdi-information-outline me-1"></i>
          <strong>Important:</strong> Make sure you have added the public key to the target host:
          <pre className="mt-2 p-2 bg-light small mb-0">{state.public_key}</pre>
        </div>
      )}
    </div>
  )
}