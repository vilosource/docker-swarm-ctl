import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import PageTitle from '@/components/common/PageTitle'
import { networksApi } from '@/api/networks'
import { hostsApi } from '@/api/hosts'
import { formatDate } from '@/utils/format'

export default function HostNetworks() {
  const { hostId } = useParams<{ hostId: string }>()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Fetch host details
  const { data: host } = useQuery({
    queryKey: ['hosts', hostId],
    queryFn: () => hostsApi.get(hostId!),
    enabled: !!hostId,
  })

  // Fetch networks
  const { data: networks = [], isLoading, error } = useQuery({
    queryKey: ['networks', hostId],
    queryFn: () => networksApi.list({ host_id: hostId }),
    enabled: !!hostId,
  })

  const createNetworkMutation = useMutation({
    mutationFn: (data: any) => networksApi.create(data, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networks', hostId] })
      setShowCreateModal(false)
    },
    onError: (error: any) => {
      console.error('Failed to create network:', error)
      alert(error.response?.data?.detail || 'Failed to create network')
    }
  })

  const deleteNetworkMutation = useMutation({
    mutationFn: (networkId: string) => networksApi.delete(networkId, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networks', hostId] })
    },
  })

  const handleDelete = (network: any) => {
    if (confirm(`Are you sure you want to delete network "${network.Name}"?`)) {
      deleteNetworkMutation.mutate(network.Id)
    }
  }

  const isSystemNetwork = (network: any) => {
    return ['bridge', 'host', 'none'].includes(network.Name)
  }

  if (isLoading) {
    return (
      <>
        <PageTitle 
          title="Networks" 
          breadcrumb={[
            { title: 'Hosts', href: '/hosts' },
            { title: 'Loading...', href: '#' },
            { title: 'Networks' }
          ]}
        />
        <div className="text-center py-4">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageTitle 
          title="Networks" 
          breadcrumb={[
            { title: 'Hosts', href: '/hosts' },
            { title: host?.display_name || host?.name || 'Host', href: `/hosts/${hostId}/system` },
            { title: 'Networks' }
          ]}
        />
        <div className="alert alert-danger">
          <i className="mdi mdi-alert-circle me-2"></i>
          Error loading networks
        </div>
      </>
    )
  }

  return (
    <>
      <PageTitle 
        title="Networks" 
        breadcrumb={[
          { title: 'Hosts', href: '/hosts' },
          { title: host?.display_name || host?.name || 'Host', href: `/hosts/${hostId}/system` },
          { title: 'Networks' }
        ]}
      />

      {/* Networks Table */}
      <div className="card">
        <div className="card-body">
          <div className="row mb-2">
            <div className="col-sm-8">
              <h5 className="card-title">Networks</h5>
            </div>
            <div className="col-sm-4">
              <div className="text-sm-end">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn btn-primary mb-2"
                >
                  <i className="mdi mdi-plus-circle me-2"></i> Create Network
                </button>
              </div>
            </div>
          </div>
          
          {networks.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <i className="mdi mdi-lan font-24 mb-3 d-block"></i>
              <p>No networks found on this host</p>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setShowCreateModal(true)}
              >
                <i className="mdi mdi-plus-circle me-1"></i>
                Create Network
              </button>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Driver</th>
                    <th>Scope</th>
                    <th>Internal</th>
                    <th>Containers</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {networks.map((network: any) => (
                    <tr key={network.Id}>
                      <td>
                        <strong>{network.Name}</strong>
                        {network.Labels && Object.keys(network.Labels).length > 0 && (
                          <div className="small text-muted">
                            {Object.entries(network.Labels).map(([key, value]) => (
                              <span key={key} className="badge bg-soft-secondary text-secondary me-1">
                                {key}: {value as string}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td>{network.Driver}</td>
                      <td>
                        <span className={`badge bg-soft-${network.Scope === 'local' ? 'info' : 'primary'} text-${network.Scope === 'local' ? 'info' : 'primary'}`}>
                          {network.Scope}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${network.Internal ? 'bg-soft-warning text-warning' : 'bg-soft-success text-success'}`}>
                          {network.Internal ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <span className="badge bg-soft-primary text-primary">
                          {network.Containers ? Object.keys(network.Containers).length : 0}
                        </span>
                      </td>
                      <td className="text-muted">
                        {network.Created ? formatDate(network.Created) : '-'}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(network)}
                          disabled={deleteNetworkMutation.isPending || isSystemNetwork(network)}
                          title={isSystemNetwork(network) ? 'Cannot delete system network' : 'Delete network'}
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

      {/* Create Network Modal */}
      {showCreateModal && (
        <>
          <div className="modal-backdrop fade show"></div>
          <div className="modal fade show d-block" tabIndex={-1}>
            <div className="modal-dialog">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">Create Network</h5>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={() => setShowCreateModal(false)}
                  ></button>
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    const formData = new FormData(e.currentTarget)
                    createNetworkMutation.mutate({
                      name: formData.get('name') as string,
                      driver: formData.get('driver') as string || 'bridge',
                      internal: formData.get('internal') === 'on',
                      attachable: formData.get('attachable') === 'on',
                    })
                  }}
                >
                  <div className="modal-body">
                    <div className="mb-3">
                      <label className="form-label">Network Name</label>
                      <input
                        type="text"
                        className="form-control"
                        name="name"
                        required
                        placeholder="my-network"
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label">Driver</label>
                      <select className="form-select" name="driver">
                        <option value="bridge">bridge</option>
                        <option value="overlay">overlay</option>
                        <option value="macvlan">macvlan</option>
                      </select>
                    </div>
                    <div className="mb-3">
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          name="internal"
                          id="internal"
                        />
                        <label className="form-check-label" htmlFor="internal">
                          Internal (no external connectivity)
                        </label>
                      </div>
                    </div>
                    <div className="mb-3">
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          name="attachable"
                          id="attachable"
                          defaultChecked
                        />
                        <label className="form-check-label" htmlFor="attachable">
                          Attachable (containers can attach)
                        </label>
                      </div>
                    </div>
                  </div>
                  <div className="modal-footer">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setShowCreateModal(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={createNetworkMutation.isPending}
                    >
                      {createNetworkMutation.isPending ? 'Creating...' : 'Create'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}