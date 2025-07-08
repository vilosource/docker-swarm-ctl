import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSecrets, useCreateSecret, useRemoveSecret } from '../hooks/useSecrets'
import { useConfigs, useCreateConfig, useRemoveConfig } from '../hooks/useConfigs'
import { formatDistanceToNow } from 'date-fns'

export default function SecretsConfigs() {
  const { hostId } = useParams<{ hostId: string }>()
  const [activeTab, setActiveTab] = useState<'secrets' | 'configs'>('secrets')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedItem, setSelectedItem] = useState<any>(null)
  const [newItemName, setNewItemName] = useState('')
  const [newItemData, setNewItemData] = useState('')

  const { data: secretsData, isLoading: secretsLoading, refetch: refetchSecrets } = useSecrets(hostId || '')
  const { data: configsData, isLoading: configsLoading, refetch: refetchConfigs } = useConfigs(hostId || '')
  
  const createSecret = useCreateSecret()
  const removeSecret = useRemoveSecret()
  const createConfig = useCreateConfig()
  const removeConfig = useRemoveConfig()

  const isSecrets = activeTab === 'secrets'
  const data = isSecrets ? secretsData : configsData
  const items = data ? (isSecrets ? data.secrets : data.configs) : []
  const isLoading = isSecrets ? secretsLoading : configsLoading

  const handleCreate = async () => {
    if (!hostId || !newItemName || !newItemData) return

    const encodedData = btoa(newItemData) // Base64 encode

    try {
      if (isSecrets) {
        await createSecret.mutateAsync({
          hostId,
          data: { name: newItemName, data: encodedData }
        })
      } else {
        await createConfig.mutateAsync({
          hostId,
          data: { name: newItemName, data: encodedData }
        })
      }
      setShowCreateModal(false)
      setNewItemName('')
      setNewItemData('')
    } catch (error) {
      console.error(`Failed to create ${isSecrets ? 'secret' : 'config'}:`, error)
    }
  }

  const handleDelete = async () => {
    if (!hostId || !selectedItem) return

    try {
      if (isSecrets) {
        await removeSecret.mutateAsync({
          hostId,
          secretId: selectedItem.ID
        })
      } else {
        await removeConfig.mutateAsync({
          hostId,
          configId: selectedItem.ID
        })
      }
      setShowDeleteModal(false)
      setSelectedItem(null)
    } catch (error) {
      console.error(`Failed to delete ${isSecrets ? 'secret' : 'config'}:`, error)
    }
  }

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id)
  }

  if (!hostId) {
    return (
      <div className="row">
        <div className="col-12">
          <div className="alert alert-danger">No host ID provided</div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              <button
                className="btn btn-secondary me-2"
                onClick={() => isSecrets ? refetchSecrets() : refetchConfigs()}
              >
                <i className="mdi mdi-refresh me-1"></i>
                Refresh
              </button>
              <button
                className="btn btn-primary"
                onClick={() => setShowCreateModal(true)}
              >
                <i className="mdi mdi-plus me-1"></i>
                Create {isSecrets ? 'Secret' : 'Config'}
              </button>
            </div>
            <h4 className="page-title">Secrets & Configs</h4>
          </div>
        </div>
      </div>

      {/* Tabs and Content */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              {/* Tabs */}
              <ul className="nav nav-tabs nav-bordered mb-3">
                <li className="nav-item">
                  <a
                    href="#"
                    className={`nav-link ${activeTab === 'secrets' ? 'active' : ''}`}
                    onClick={(e) => {
                      e.preventDefault()
                      setActiveTab('secrets')
                    }}
                  >
                    <i className="mdi mdi-key-variant me-1"></i>
                    Secrets
                  </a>
                </li>
                <li className="nav-item">
                  <a
                    href="#"
                    className={`nav-link ${activeTab === 'configs' ? 'active' : ''}`}
                    onClick={(e) => {
                      e.preventDefault()
                      setActiveTab('configs')
                    }}
                  >
                    <i className="mdi mdi-cog me-1"></i>
                    Configs
                  </a>
                </li>
              </ul>

              {/* Tab Content */}
              {isLoading ? (
                <div className="d-flex justify-content-center py-4">
                  <div className="spinner-border" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                </div>
              ) : items.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-muted mb-0">No {isSecrets ? 'secrets' : 'configs'} found</p>
                  <button
                    className="btn btn-sm btn-primary mt-2"
                    onClick={() => setShowCreateModal(true)}
                  >
                    Create your first {isSecrets ? 'secret' : 'config'}
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover mb-0">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>ID</th>
                        <th>Created</th>
                        <th>Labels</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => (
                        <tr key={item.ID}>
                          <td>
                            <strong>{item.Spec.Name}</strong>
                          </td>
                          <td>
                            <div className="d-flex align-items-center">
                              <code className="text-muted">
                                {item.ID.substring(0, 12)}...
                              </code>
                              <button
                                className="btn btn-sm btn-light ms-2"
                                onClick={() => handleCopyId(item.ID)}
                                title="Copy full ID"
                              >
                                <i className="mdi mdi-content-copy"></i>
                              </button>
                            </div>
                          </td>
                          <td>
                            <small>{formatDistanceToNow(new Date(item.CreatedAt), { addSuffix: true })}</small>
                          </td>
                          <td>
                            {item.Spec.Labels && Object.keys(item.Spec.Labels).length > 0 ? (
                              Object.entries(item.Spec.Labels).map(([key, value]) => (
                                <span
                                  key={key}
                                  className="badge bg-light text-dark me-1"
                                >
                                  {key}: {value}
                                </span>
                              ))
                            ) : (
                              '-'
                            )}
                          </td>
                          <td>
                            <button
                              className="btn btn-sm btn-light text-danger"
                              onClick={() => {
                                setSelectedItem(item)
                                setShowDeleteModal(true)
                              }}
                              title="Delete"
                            >
                              <i className="mdi mdi-delete"></i>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Create {isSecrets ? 'Secret' : 'Config'}</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => {
                    setShowCreateModal(false)
                    setNewItemName('')
                    setNewItemData('')
                  }}
                ></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label">Name</label>
                  <input
                    type="text"
                    className="form-control"
                    value={newItemName}
                    onChange={(e) => setNewItemName(e.target.value)}
                    placeholder="Enter a unique name"
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label">Data</label>
                  <textarea
                    className="form-control"
                    rows={4}
                    value={newItemData}
                    onChange={(e) => setNewItemData(e.target.value)}
                    placeholder={isSecrets ? 
                      "Enter sensitive data that will be encrypted and stored securely" : 
                      "Enter configuration data that will be available to services"
                    }
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowCreateModal(false)
                    setNewItemName('')
                    setNewItemData('')
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCreate}
                  disabled={!newItemName || !newItemData || createSecret.isPending || createConfig.isPending}
                >
                  {(createSecret.isPending || createConfig.isPending) ? 'Creating...' : 'Create'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Delete {isSecrets ? 'Secret' : 'Config'}</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => {
                    setShowDeleteModal(false)
                    setSelectedItem(null)
                  }}
                ></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-warning">
                  This action cannot be undone. Services using this {isSecrets ? 'secret' : 'config'} may fail.
                </div>
                <p>
                  Are you sure you want to delete <strong>{selectedItem?.Spec.Name}</strong>?
                </p>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowDeleteModal(false)
                    setSelectedItem(null)
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={handleDelete}
                  disabled={removeSecret.isPending || removeConfig.isPending}
                >
                  {(removeSecret.isPending || removeConfig.isPending) ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Backdrop */}
      {(showCreateModal || showDeleteModal) && (
        <div className="modal-backdrop fade show"></div>
      )}
    </>
  )
}