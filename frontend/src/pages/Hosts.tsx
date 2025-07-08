import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { hostsApi } from '@/api/hosts'
import { DockerHost, HostStatus } from '@/types'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/hooks/useToast'
import AddHostModal from '@/components/hosts/AddHostModal'
import EditHostModal from '@/components/hosts/EditHostModal'

export default function Hosts() {
  const { user } = useAuthStore()
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingHost, setEditingHost] = useState<DockerHost | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['hosts'],
    queryFn: () => hostsApi.list()
  })

  const testConnectionMutation = useMutation({
    mutationFn: (hostId: string) => hostsApi.testConnection(hostId),
    onSuccess: (result, hostId) => {
      if (result.success) {
        showToast('Connection successful', 'success')
        queryClient.invalidateQueries({ queryKey: ['hosts'] })
      } else {
        showToast(result.error || 'Connection failed', 'error')
      }
    },
    onError: (error) => {
      showToast('Failed to test connection', 'error')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (hostId: string) => hostsApi.delete(hostId),
    onSuccess: () => {
      showToast('Host deleted successfully', 'success')
      queryClient.invalidateQueries({ queryKey: ['hosts'] })
    },
    onError: (error) => {
      showToast('Failed to delete host', 'error')
    }
  })

  const getStatusBadge = (status: HostStatus) => {
    switch (status) {
      case 'healthy':
        return <span className="badge bg-success">Healthy</span>
      case 'unhealthy':
        return <span className="badge bg-danger">Unhealthy</span>
      case 'pending':
        return <span className="badge bg-warning">Pending</span>
      case 'unreachable':
        return <span className="badge bg-secondary">Unreachable</span>
      default:
        return <span className="badge bg-secondary">{status}</span>
    }
  }

  const getHostTypeLabel = (host: DockerHost) => {
    switch (host.host_type) {
      case 'swarm_manager':
        return (
          <span className="text-primary">
            <i className="mdi mdi-crown me-1"></i>
            {host.is_leader ? 'Swarm Leader' : 'Swarm Manager'}
          </span>
        )
      case 'swarm_worker':
        return (
          <span className="text-info">
            <i className="mdi mdi-worker me-1"></i>
            Swarm Worker
          </span>
        )
      default:
        return (
          <span className="text-muted">
            <i className="mdi mdi-server me-1"></i>
            Standalone
          </span>
        )
    }
  }

  const handleDelete = async (host: DockerHost) => {
    if (window.confirm(`Are you sure you want to delete host "${host.name}"?`)) {
      deleteMutation.mutate(host.id)
    }
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
      <div className="alert alert-danger">
        Failed to load hosts: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  const hosts = data?.items || []

  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              <button
                className="btn btn-primary"
                onClick={() => setShowAddModal(true)}
              >
                <i className="mdi mdi-plus me-1"></i>
                Add Host
              </button>
            </div>
            <h4 className="page-title">Docker Hosts</h4>
          </div>
        </div>
      </div>

      {/* Hosts List */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              {hosts.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-muted mb-0">No hosts configured</p>
                  <button
                    className="btn btn-sm btn-primary mt-2"
                    onClick={() => setShowAddModal(true)}
                  >
                    Add your first host
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover mb-0">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Connection</th>
                        <th>Status</th>
                        <th>Version</th>
                        <th>Last Check</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {hosts.map((host) => (
                        <tr key={host.id}>
                          <td>
                            <h5 className="font-14 mb-0">
                              {host.name}
                              {host.is_default && (
                                <span className="badge bg-primary ms-2">Default</span>
                              )}
                            </h5>
                            {host.description && (
                              <small className="text-muted">{host.description}</small>
                            )}
                          </td>
                          <td>{getHostTypeLabel(host)}</td>
                          <td>
                            <code className="text-muted">{host.host_url}</code>
                            <br />
                            <small className="text-muted">{host.connection_type.toUpperCase()}</small>
                          </td>
                          <td>{getStatusBadge(host.status)}</td>
                          <td>
                            {host.docker_version ? (
                              <div>
                                <small>Docker {host.docker_version}</small>
                                <br />
                                <small className="text-muted">API {host.api_version}</small>
                              </div>
                            ) : (
                              <span className="text-muted">-</span>
                            )}
                          </td>
                          <td>
                            {host.last_health_check ? (
                              <small>{format(new Date(host.last_health_check), 'MMM dd, HH:mm')}</small>
                            ) : (
                              <span className="text-muted">Never</span>
                            )}
                          </td>
                          <td>
                            <div className="btn-group btn-group-sm" role="group">
                              <button
                                className="btn btn-light"
                                onClick={() => navigate(`/hosts/${host.id}/swarm`)}
                                title="Swarm"
                              >
                                <i className="mdi mdi-cloud"></i>
                              </button>
                              <button
                                className="btn btn-light"
                                onClick={() => testConnectionMutation.mutate(host.id)}
                                disabled={testConnectionMutation.isPending}
                                title="Test Connection"
                              >
                                <i className="mdi mdi-connection"></i>
                              </button>
                              <button
                                className="btn btn-light"
                                onClick={() => setEditingHost(host)}
                                title="Edit"
                              >
                                <i className="mdi mdi-pencil"></i>
                              </button>
                              <button
                                className="btn btn-light text-danger"
                                onClick={() => handleDelete(host)}
                                disabled={deleteMutation.isPending}
                                title="Delete"
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

      {/* Host Tags Summary */}
      {hosts.some(h => h.tags.length > 0) && (
        <div className="row">
          <div className="col-12">
            <div className="card">
              <div className="card-body">
                <h5 className="card-title">Host Tags</h5>
                <div className="tags-container">
                  {hosts.flatMap(host => 
                    host.tags.map(tag => (
                      <span key={`${host.id}-${tag.id}`} className="badge bg-light text-dark me-2 mb-2">
                        <strong>{tag.tag_name}:</strong> {tag.tag_value || 'true'}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Host Modal */}
      {showAddModal && (
        <AddHostModal
          show={showAddModal}
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false)
            queryClient.invalidateQueries({ queryKey: ['hosts'] })
          }}
        />
      )}

      {/* Edit Host Modal */}
      {editingHost && (
        <EditHostModal
          show={!!editingHost}
          host={editingHost}
          onClose={() => setEditingHost(null)}
          onSuccess={() => {
            setEditingHost(null)
            queryClient.invalidateQueries({ queryKey: ['hosts'] })
          }}
        />
      )}
    </>
  )
}