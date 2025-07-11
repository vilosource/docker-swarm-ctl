import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { hostsApi } from '@/api/hosts'
import { DockerHostCreate, HostType, ConnectionType } from '@/types'
import { useToast } from '@/hooks/useToast'
import { SSHHostWizard } from '@/components/wizards'

interface AddHostModalProps {
  show: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddHostModal({ show, onClose, onSuccess }: AddHostModalProps) {
  const { showToast } = useToast()
  const [showSSHWizard, setShowSSHWizard] = useState(false)
  const [formData, setFormData] = useState<DockerHostCreate>({
    name: '',
    display_name: '',
    description: '',
    host_type: 'standalone',
    connection_type: 'tcp',
    host_url: 'tcp://localhost:2375',
    is_active: true,
    is_default: false,
    tags: [],
    credentials: []
  })

  const [showCredentials, setShowCredentials] = useState(false)
  const [tlsCert, setTlsCert] = useState('')
  const [tlsKey, setTlsKey] = useState('')
  const [tlsCa, setTlsCa] = useState('')

  const createMutation = useMutation({
    mutationFn: (data: DockerHostCreate) => hostsApi.create(data),
    onSuccess: () => {
      showToast('Host created successfully', 'success')
      onSuccess()
    },
    onError: (error) => {
      showToast('Failed to create host', 'error')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Use SSH wizard for SSH connections
    if (formData.connection_type === 'ssh') {
      setShowSSHWizard(true)
      return
    }
    
    const credentials = []
    if (showCredentials && formData.connection_type === 'tcp') {
      if (tlsCert) credentials.push({ credential_type: 'tls_cert', credential_value: tlsCert })
      if (tlsKey) credentials.push({ credential_type: 'tls_key', credential_value: tlsKey })
      if (tlsCa) credentials.push({ credential_type: 'tls_ca', credential_value: tlsCa })
    }
    
    createMutation.mutate({
      ...formData,
      credentials
    })
  }

  const updateConnectionUrl = (type: ConnectionType) => {
    let url = formData.host_url
    if (type === 'unix') {
      url = 'unix:///var/run/docker.sock'
    } else if (type === 'tcp') {
      url = showCredentials ? 'tcp://localhost:2376' : 'tcp://localhost:2375'
    } else if (type === 'ssh') {
      url = 'ssh://user@localhost'
    }
    setFormData({ ...formData, connection_type: type, host_url: url })
  }

  if (!show && !showSSHWizard) return null

  // Show SSH wizard instead of modal if SSH connection is chosen
  if (showSSHWizard) {
    return (
      <SSHHostWizard
        open={showSSHWizard}
        onClose={() => {
          setShowSSHWizard(false)
          onClose()
        }}
        onComplete={(hostId) => {
          setShowSSHWizard(false)
          onSuccess()
        }}
      />
    )
  }

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Add Docker Host</h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label">Host Name *</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    placeholder="e.g., docker-1.lab.viloforge.com"
                  />
                </div>
                
                <div className="col-md-6">
                  <label className="form-label">Display Name</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.display_name || ''}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    placeholder="e.g., Docker 1"
                    maxLength={100}
                  />
                  <small className="text-muted">Short name for navigation menu</small>
                </div>
                
                <div className="col-md-6">
                  <label className="form-label">Host Type</label>
                  <select
                    className="form-select"
                    value={formData.host_type}
                    onChange={(e) => setFormData({ ...formData, host_type: e.target.value as HostType })}
                  >
                    <option value="standalone">Standalone</option>
                    <option value="swarm_manager">Swarm Manager</option>
                    <option value="swarm_worker">Swarm Worker</option>
                  </select>
                </div>
                
                <div className="col-12">
                  <label className="form-label">Description</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Optional description"
                  />
                </div>
                
                <div className="col-md-4">
                  <label className="form-label">Connection Type</label>
                  <select
                    className="form-select"
                    value={formData.connection_type}
                    onChange={(e) => updateConnectionUrl(e.target.value as ConnectionType)}
                  >
                    <option value="unix">Unix Socket</option>
                    <option value="tcp">TCP</option>
                    <option value="ssh">SSH</option>
                  </select>
                </div>
                
                <div className="col-md-8">
                  <label className="form-label">Connection URL *</label>
                  <input
                    type="text"
                    className="form-control"
                    value={formData.host_url}
                    onChange={(e) => setFormData({ ...formData, host_url: e.target.value })}
                    required
                    placeholder="e.g., tcp://192.168.1.100:2376"
                  />
                  <small className="text-muted">
                    {formData.connection_type === 'unix' && 'Local Docker socket path'}
                    {formData.connection_type === 'tcp' && 'Remote Docker API endpoint'}
                    {formData.connection_type === 'ssh' && 'SSH connection string'}
                  </small>
                </div>
                
                {formData.connection_type === 'ssh' && (
                  <div className="col-12">
                    <div className="alert alert-info">
                      <i className="mdi mdi-information-outline me-1"></i>
                      SSH connections require additional setup. Click "Create Host" to start the SSH configuration wizard.
                    </div>
                  </div>
                )}
                
                {formData.connection_type === 'tcp' && (
                  <div className="col-12">
                    <div className="form-check">
                      <input
                        type="checkbox"
                        className="form-check-input"
                        id="useTls"
                        checked={showCredentials}
                        onChange={(e) => setShowCredentials(e.target.checked)}
                      />
                      <label className="form-check-label" htmlFor="useTls">
                        Use TLS Authentication
                      </label>
                    </div>
                  </div>
                )}
                
                {showCredentials && formData.connection_type === 'tcp' && (
                  <>
                    <div className="col-12">
                      <label className="form-label">TLS Certificate</label>
                      <textarea
                        className="form-control"
                        rows={3}
                        value={tlsCert}
                        onChange={(e) => setTlsCert(e.target.value)}
                        placeholder="-----BEGIN CERTIFICATE-----"
                      />
                    </div>
                    
                    <div className="col-12">
                      <label className="form-label">TLS Key</label>
                      <textarea
                        className="form-control"
                        rows={3}
                        value={tlsKey}
                        onChange={(e) => setTlsKey(e.target.value)}
                        placeholder="-----BEGIN RSA PRIVATE KEY-----"
                      />
                    </div>
                    
                    <div className="col-12">
                      <label className="form-label">CA Certificate</label>
                      <textarea
                        className="form-control"
                        rows={3}
                        value={tlsCa}
                        onChange={(e) => setTlsCa(e.target.value)}
                        placeholder="-----BEGIN CERTIFICATE-----"
                      />
                    </div>
                  </>
                )}
                
                <div className="col-md-6">
                  <div className="form-check">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      id="isActive"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="isActive">
                      Active
                    </label>
                  </div>
                </div>
                
                <div className="col-md-6">
                  <div className="form-check">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      id="isDefault"
                      checked={formData.is_default}
                      onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    />
                    <label className="form-check-label" htmlFor="isDefault">
                      Set as Default Host
                    </label>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 
                 formData.connection_type === 'ssh' ? 'Start SSH Setup' : 'Create Host'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}