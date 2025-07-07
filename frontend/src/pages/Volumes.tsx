import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import PageTitle from '@/components/common/PageTitle'
import { volumesApi } from '@/api/volumes'
import { hostsApi } from '@/api/hosts'
import { HostHealthIndicator } from '@/components/common/HostHealthIndicator'
import { formatBytes } from '@/utils/format'
import { Volume } from '@/types/volume'

export default function Volumes() {
  const [searchParams] = useSearchParams()
  const hostId = searchParams.get('host_id')
  const queryClient = useQueryClient()
  const [selectedVolumes, setSelectedVolumes] = useState<Set<string>>(new Set())

  // Fetch volumes
  const { data: volumes = [], isLoading, error } = useQuery({
    queryKey: ['volumes', hostId],
    queryFn: () => volumesApi.list({ host_id: hostId || undefined })
  })

  // Fetch hosts for filtering
  const { data: hostsData } = useQuery({
    queryKey: ['hosts', 'active'],
    queryFn: () => hostsApi.list({ active_only: true })
  })

  const hosts = hostsData?.items || []

  // Delete volume mutation
  const deleteMutation = useMutation({
    mutationFn: ({ name, hostId }: { name: string; hostId?: string }) => 
      volumesApi.remove(name, false, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['volumes'] })
      setSelectedVolumes(new Set())
    }
  })

  // Prune volumes mutation
  const pruneMutation = useMutation({
    mutationFn: (hostId?: string) => volumesApi.prune(undefined, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['volumes'] })
    }
  })

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedVolumes(new Set(volumes.map(v => v.name)))
    } else {
      setSelectedVolumes(new Set())
    }
  }

  const handleSelect = (volumeName: string) => {
    const newSelected = new Set(selectedVolumes)
    if (newSelected.has(volumeName)) {
      newSelected.delete(volumeName)
    } else {
      newSelected.add(volumeName)
    }
    setSelectedVolumes(newSelected)
  }

  const getHostInfo = (volume: Volume) => {
    if (!volume.host_id) return null
    const host = hosts.find(h => h.id === volume.host_id)
    return host
  }

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="alert alert-danger">
        <i className="mdi mdi-alert-circle me-2"></i>
        Error loading volumes
      </div>
    )
  }

  return (
    <>
      <PageTitle 
        title="Volumes" 
        breadcrumb={[
          { title: 'Resources', href: '#' },
          { title: 'Volumes' }
        ]}
        actions={
          <div className="d-flex gap-2">
            <Link to="/volumes/create" className="btn btn-primary">
              <i className="mdi mdi-plus-circle me-1"></i>
              Create Volume
            </Link>
            <button 
              className="btn btn-danger"
              onClick={() => {
                if (confirm('Are you sure you want to remove all unused volumes?')) {
                  pruneMutation.mutate(hostId || undefined)
                }
              }}
              disabled={pruneMutation.isPending}
            >
              <i className="mdi mdi-delete-sweep me-1"></i>
              Prune
            </button>
          </div>
        }
      />

      {/* Host Filter */}
      {!hostId && hosts.length > 1 && (
        <div className="card mb-3">
          <div className="card-body">
            <div className="d-flex align-items-center gap-3">
              <label className="mb-0">Filter by host:</label>
              <div className="btn-group btn-group-sm">
                <Link 
                  to="/volumes"
                  className="btn btn-outline-primary active"
                >
                  All Hosts
                </Link>
                {hosts.map(host => (
                  <Link
                    key={host.id}
                    to={`/volumes?host_id=${host.id}`}
                    className="btn btn-outline-primary"
                  >
                    {host.display_name || host.name}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Volumes Table */}
      <div className="card">
        <div className="card-body">
          {volumes.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <i className="mdi mdi-database font-24 mb-3 d-block"></i>
              <p>No volumes found</p>
              <Link to="/volumes/create" className="btn btn-primary btn-sm">
                <i className="mdi mdi-plus-circle me-1"></i>
                Create Volume
              </Link>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead>
                  <tr>
                    <th style={{ width: '40px' }}>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        onChange={handleSelectAll}
                        checked={selectedVolumes.size === volumes.length && volumes.length > 0}
                      />
                    </th>
                    <th>Name</th>
                    <th>Driver</th>
                    <th>Scope</th>
                    <th>Mount Point</th>
                    {!hostId && <th>Host</th>}
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {volumes.map((volume) => {
                    const host = getHostInfo(volume)
                    return (
                      <tr key={`${volume.host_id}-${volume.name}`}>
                        <td>
                          <input
                            type="checkbox"
                            className="form-check-input"
                            checked={selectedVolumes.has(volume.name)}
                            onChange={() => handleSelect(volume.name)}
                          />
                        </td>
                        <td>
                          <strong>{volume.name}</strong>
                          {volume.labels && Object.keys(volume.labels).length > 0 && (
                            <div className="small text-muted">
                              {Object.entries(volume.labels).map(([key, value]) => (
                                <span key={key} className="badge bg-soft-secondary text-secondary me-1">
                                  {key}: {value}
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
                        {!hostId && (
                          <td>
                            {host ? (
                              <div className="d-flex align-items-center gap-2">
                                <HostHealthIndicator status={host.status} size="sm" />
                                <Link to={`/volumes?host_id=${host.id}`}>
                                  {host.display_name || host.name}
                                </Link>
                              </div>
                            ) : (
                              <span className="text-muted">Unknown</span>
                            )}
                          </td>
                        )}
                        <td>
                          {volume.created_at ? new Date(volume.created_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td>
                          <div className="btn-group btn-group-sm">
                            <Link 
                              to={`/volumes/${volume.name}?host_id=${volume.host_id}`}
                              className="btn btn-soft-info"
                              title="View details"
                            >
                              <i className="mdi mdi-information-outline"></i>
                            </Link>
                            <button
                              className="btn btn-soft-danger"
                              title="Delete volume"
                              onClick={() => {
                                if (confirm(`Are you sure you want to delete volume "${volume.name}"?`)) {
                                  deleteMutation.mutate({ name: volume.name, hostId: volume.host_id })
                                }
                              }}
                              disabled={deleteMutation.isPending}
                            >
                              <i className="mdi mdi-delete"></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}