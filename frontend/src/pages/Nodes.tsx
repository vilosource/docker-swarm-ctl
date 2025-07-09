import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useNodes, useUpdateNode, useRemoveNode } from '../hooks/useNodes'
import { formatDistanceToNow } from 'date-fns'

export default function Nodes() {
  const { hostId } = useParams<{ hostId: string }>()
  const navigate = useNavigate()
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [showUpdateModal, setShowUpdateModal] = useState(false)
  const [showRemoveModal, setShowRemoveModal] = useState(false)
  const [availability, setAvailability] = useState<string>('')
  const [role, setRole] = useState<string>('')

  const { data, isLoading, error, refetch } = useNodes(hostId || '')
  const updateNode = useUpdateNode()
  const removeNode = useRemoveNode()

  const handleUpdateClick = (node: any) => {
    setSelectedNode(node)
    setAvailability(node.availability)
    setRole(node.role)
    setShowUpdateModal(true)
  }

  const handleRemoveClick = (node: any) => {
    setSelectedNode(node)
    setShowRemoveModal(true)
  }

  const handleUpdateNode = async () => {
    if (!hostId || !selectedNode) return

    const updates: any = {}
    if (availability !== selectedNode.availability) {
      updates.availability = availability
    }
    if (role !== selectedNode.role) {
      updates.role = role
    }

    try {
      await updateNode.mutateAsync({
        hostId,
        nodeId: selectedNode.id,
        version: selectedNode.version,
        update: updates,
      })
      setShowUpdateModal(false)
      setSelectedNode(null)
    } catch (error) {
      console.error('Failed to update node:', error)
    }
  }

  const handleRemoveNode = async (force: boolean) => {
    if (!hostId || !selectedNode) return

    try {
      await removeNode.mutateAsync({
        hostId,
        nodeId: selectedNode.id,
        force,
      })
      setShowRemoveModal(false)
      setSelectedNode(null)
    } catch (error) {
      console.error('Failed to remove node:', error)
    }
  }

  const getAvailabilityBadge = (availability: string) => {
    switch (availability) {
      case 'active':
        return <span className="badge bg-success">Active</span>
      case 'pause':
        return <span className="badge bg-warning">Paused</span>
      case 'drain':
        return <span className="badge bg-danger">Drained</span>
      default:
        return <span className="badge bg-secondary">{availability}</span>
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ready':
        return <span className="badge bg-success">Ready</span>
      case 'down':
        return <span className="badge bg-danger">Down</span>
      case 'unknown':
        return <span className="badge bg-secondary">Unknown</span>
      default:
        return <span className="badge bg-secondary">{status}</span>
    }
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

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="row">
        <div className="col-12">
          <div className="alert alert-danger">
            Failed to load nodes: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </div>
      </div>
    )
  }

  const nodes = data?.nodes || []

  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              <button
                className="btn btn-secondary me-2"
                onClick={() => refetch()}
              >
                <i className="mdi mdi-refresh me-1"></i>
                Refresh
              </button>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/hosts/${hostId}/swarm/join`)}
              >
                <i className="mdi mdi-plus me-1"></i>
                Add Node
              </button>
            </div>
            <h4 className="page-title">
              <i className="mdi mdi-server-network me-2"></i>
              Swarm Nodes
            </h4>
          </div>
        </div>
      </div>

      {/* Nodes Table */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              {nodes.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-muted mb-0">No nodes found</p>
                  <button
                    className="btn btn-sm btn-primary mt-2"
                    onClick={() => navigate(`/hosts/${hostId}/swarm/join`)}
                  >
                    Add your first node
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover mb-0">
                    <thead>
                      <tr>
                        <th>Hostname</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Availability</th>
                        <th>Engine Version</th>
                        <th>IP Address</th>
                        <th>Last Updated</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nodes.map((node) => (
                        <tr key={node.id}>
                          <td>
                            <strong>{node.hostname}</strong>
                            {node.is_leader && (
                              <span className="badge bg-warning ms-2">
                                <i className="mdi mdi-crown me-1"></i>
                                Leader
                              </span>
                            )}
                          </td>
                          <td>
                            {node.role === 'manager' ? (
                              <span className="text-primary">
                                <i className="mdi mdi-shield-crown me-1"></i>
                                Manager
                              </span>
                            ) : (
                              <span className="text-info">
                                <i className="mdi mdi-worker me-1"></i>
                                Worker
                              </span>
                            )}
                          </td>
                          <td>{getStatusBadge(node.state)}</td>
                          <td>{getAvailabilityBadge(node.availability)}</td>
                          <td>{node.engine_version || '-'}</td>
                          <td>
                            <code className="text-muted">{node.addr}</code>
                          </td>
                          <td>
                            <small>
                              {node.updated_at 
                                ? formatDistanceToNow(new Date(node.updated_at), { addSuffix: true })
                                : 'Unknown'
                              }
                            </small>
                          </td>
                          <td>
                            <div className="btn-group btn-group-sm">
                              <button
                                className="btn btn-light"
                                onClick={() => handleUpdateClick(node)}
                                title="Update Node"
                              >
                                <i className="mdi mdi-pencil"></i>
                              </button>
                              <button
                                className="btn btn-light text-danger"
                                onClick={() => handleRemoveClick(node)}
                                title="Remove Node"
                              >
                                <i className="mdi mdi-delete"></i>
                              </button>
                            </div>
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

      {/* Update Node Modal */}
      {showUpdateModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Update Node</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowUpdateModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label">Availability</label>
                  <select
                    className="form-select"
                    value={availability}
                    onChange={(e) => setAvailability(e.target.value)}
                  >
                    <option value="active">Active</option>
                    <option value="pause">Pause</option>
                    <option value="drain">Drain</option>
                  </select>
                </div>

                {selectedNode?.role === 'worker' && (
                  <div className="mb-3">
                    <label className="form-label">Role</label>
                    <select
                      className="form-select"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                    >
                      <option value="worker">Worker</option>
                      <option value="manager">Manager</option>
                    </select>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowUpdateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleUpdateNode}
                  disabled={updateNode.isPending}
                >
                  {updateNode.isPending ? 'Updating...' : 'Update'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Remove Node Modal */}
      {showRemoveModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Remove Node</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowRemoveModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-warning">
                  This will remove the node from the swarm. Any tasks running on this node will be rescheduled.
                </div>
                <p>
                  Are you sure you want to remove node <strong>{selectedNode?.hostname}</strong>?
                </p>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowRemoveModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-warning"
                  onClick={() => handleRemoveNode(false)}
                  disabled={removeNode.isPending}
                >
                  Remove
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => handleRemoveNode(true)}
                  disabled={removeNode.isPending}
                >
                  Force Remove
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Backdrop */}
      {(showUpdateModal || showRemoveModal) && (
        <div className="modal-backdrop fade show"></div>
      )}
    </>
  )
}