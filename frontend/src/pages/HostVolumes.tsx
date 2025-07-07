import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import PageTitle from '@/components/common/PageTitle'
import { volumesApi } from '@/api/volumes'
import { hostsApi } from '@/api/hosts'
import { formatDate } from '@/utils/format'

export default function HostVolumes() {
  const { hostId } = useParams<{ hostId: string }>()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Fetch host details
  const { data: host } = useQuery({
    queryKey: ['hosts', hostId],
    queryFn: () => hostsApi.get(hostId!),
    enabled: !!hostId,
  })

  // Fetch volumes
  const { data: volumes = [], isLoading, error } = useQuery({
    queryKey: ['volumes', hostId],
    queryFn: () => volumesApi.list({ host_id: hostId }),
    enabled: !!hostId,
  })

  const createVolumeMutation = useMutation({
    mutationFn: (data: any) => volumesApi.create(data, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['volumes', hostId] })
      setShowCreateModal(false)
    },
    onError: (error: any) => {
      console.error('Failed to create volume:', error)
      alert(error.response?.data?.detail || 'Failed to create volume')
    }
  })

  const deleteVolumeMutation = useMutation({
    mutationFn: (volumeName: string) => volumesApi.remove(volumeName, false, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['volumes', hostId] })
    },
  })

  const handleDelete = (volumeName: string) => {
    if (confirm(`Are you sure you want to delete volume "${volumeName}"?`)) {
      deleteVolumeMutation.mutate(volumeName)
    }
  }

  if (isLoading) {
    return (
      <>
        <PageTitle 
          title="Volumes" 
          breadcrumb={[
            { title: 'Hosts', href: '/hosts' },
            { title: 'Loading...', href: '#' },
            { title: 'Volumes' }
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
          title="Volumes" 
          breadcrumb={[
            { title: 'Hosts', href: '/hosts' },
            { title: host?.display_name || host?.name || 'Host', href: `/hosts/${hostId}/system` },
            { title: 'Volumes' }
          ]}
        />
        <div className="alert alert-danger">
          <i className="mdi mdi-alert-circle me-2"></i>
          Error loading volumes
        </div>
        
        {/* Create Volume Modal */}
        {showCreateModal && (
          <>
            <div className="modal-backdrop fade show"></div>
            <div className="modal fade show d-block" tabIndex={-1}>
              <div className="modal-dialog">
                <div className="modal-content">
                  <div className="modal-header">
                    <h5 className="modal-title">Create Volume</h5>
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
                      createVolumeMutation.mutate({
                        name: formData.get('name') as string,
                        driver: formData.get('driver') as string || 'local',
                      })
                    }}
                  >
                    <div className="modal-body">
                      <div className="mb-3">
                        <label className="form-label">Volume Name</label>
                        <input
                          type="text"
                          className="form-control"
                          name="name"
                          required
                          placeholder="my-volume"
                        />
                      </div>
                      <div className="mb-3">
                        <label className="form-label">Driver</label>
                        <select className="form-select" name="driver">
                          <option value="local">local</option>
                        </select>
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
                        disabled={createVolumeMutation.isPending}
                      >
                        {createVolumeMutation.isPending ? 'Creating...' : 'Create'}
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

  return (
    <>
      <PageTitle 
        title="Volumes" 
        breadcrumb={[
          { title: 'Hosts', href: '/hosts' },
          { title: host?.display_name || host?.name || 'Host', href: `/hosts/${hostId}/system` },
          { title: 'Volumes' }
        ]}
      />

      {/* Volumes Table */}
      <div className="card">
        <div className="card-body">
          <div className="row mb-2">
            <div className="col-sm-8">
              <h5 className="card-title">Volumes</h5>
            </div>
            <div className="col-sm-4">
              <div className="text-sm-end">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn btn-primary mb-2"
                >
                  <i className="mdi mdi-plus-circle me-2"></i> Create Volume
                </button>
              </div>
            </div>
          </div>
          
          {volumes.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <i className="mdi mdi-database font-24 mb-3 d-block"></i>
              <p>No volumes found on this host</p>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setShowCreateModal(true)}
              >
                <i className="mdi mdi-plus-circle me-1"></i>
                Create Volume
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
                    <th>Mount Point</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {volumes.map((volume: any) => (
                    <tr key={volume.name}>
                      <td>
                        <strong>{volume.name}</strong>
                        {volume.labels && Object.keys(volume.labels).length > 0 && (
                          <div className="small text-muted">
                            {Object.entries(volume.labels).map(([key, value]) => (
                              <span key={key} className="badge bg-soft-secondary text-secondary me-1">
                                {key}: {value as string}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td>{volume.driver}</td>
                      <td>
                        <span className={`badge bg-soft-${volume.scope === 'local' ? 'info' : 'primary'} text-${volume.scope === 'local' ? 'info' : 'primary'}`}>
                          {volume.scope}
                        </span>
                      </td>
                      <td>
                        <code className="small">{volume.mountpoint}</code>
                      </td>
                      <td className="text-muted">
                        {volume.created_at ? formatDate(volume.created_at) : '-'}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(volume.name)}
                          disabled={deleteVolumeMutation.isPending}
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

      {/* Create Volume Modal */}
      {showCreateModal && (
        <>
          <div className="modal-backdrop fade show"></div>
          <div className="modal fade show d-block" tabIndex={-1}>
            <div className="modal-dialog">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">Create Volume</h5>
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
                    createVolumeMutation.mutate({
                      name: formData.get('name') as string,
                      driver: formData.get('driver') as string || 'local',
                    })
                  }}
                >
                  <div className="modal-body">
                    <div className="mb-3">
                      <label className="form-label">Volume Name</label>
                      <input
                        type="text"
                        className="form-control"
                        name="name"
                        required
                        placeholder="my-volume"
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label">Driver</label>
                      <select className="form-select" name="driver">
                        <option value="local">local</option>
                      </select>
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
                      disabled={createVolumeMutation.isPending}
                    >
                      {createVolumeMutation.isPending ? 'Creating...' : 'Create'}
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