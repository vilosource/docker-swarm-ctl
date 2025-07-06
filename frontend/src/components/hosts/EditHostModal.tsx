import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { hostsApi } from '@/api/hosts'
import { DockerHost, DockerHostUpdate } from '@/types'
import { useToast } from '@/hooks/useToast'

interface EditHostModalProps {
  show: boolean
  host: DockerHost
  onClose: () => void
  onSuccess: () => void
}

export default function EditHostModal({ show, host, onClose, onSuccess }: EditHostModalProps) {
  const { showToast } = useToast()
  const [formData, setFormData] = useState<DockerHostUpdate>({
    name: host.name,
    display_name: host.display_name,
    description: host.description,
    host_url: host.host_url,
    is_active: host.is_active,
    is_default: host.is_default
  })

  const updateMutation = useMutation({
    mutationFn: (data: DockerHostUpdate) => hostsApi.update(host.id, data),
    onSuccess: () => {
      showToast('Host updated successfully', 'success')
      onSuccess()
    },
    onError: (error) => {
      showToast('Failed to update host', 'error')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  if (!show) return null

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Edit Docker Host</h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              <div className="mb-3">
                <label className="form-label">Host Name</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              
              <div className="mb-3">
                <label className="form-label">Display Name</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.display_name || ''}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  placeholder="Short name for navigation menu"
                  maxLength={100}
                />
                <small className="text-muted">Leave empty to auto-truncate hostname</small>
              </div>
              
              <div className="mb-3">
                <label className="form-label">Description</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
              
              <div className="mb-3">
                <label className="form-label">Connection URL</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.host_url || ''}
                  onChange={(e) => setFormData({ ...formData, host_url: e.target.value })}
                />
              </div>
              
              <div className="form-check mb-3">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="editIsActive"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
                <label className="form-check-label" htmlFor="editIsActive">
                  Active
                </label>
              </div>
              
              <div className="form-check">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="editIsDefault"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                />
                <label className="form-check-label" htmlFor="editIsDefault">
                  Set as Default Host
                </label>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? 'Updating...' : 'Update Host'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}