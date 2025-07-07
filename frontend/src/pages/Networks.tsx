import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import PageTitle from '@/components/common/PageTitle'
import { networksApi } from '@/api/networks'
import { hostsApi } from '@/api/hosts'
import { HostHealthIndicator } from '@/components/common/HostHealthIndicator'
import { Network } from '@/types/network'

export default function Networks() {
  const [searchParams] = useSearchParams()
  const hostId = searchParams.get('host_id')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedNetworks, setSelectedNetworks] = useState<Set<string>>(new Set())

  // Fetch networks
  const { data: networks = [], isLoading, error } = useQuery({
    queryKey: ['networks', hostId],
    queryFn: () => networksApi.list({ host_id: hostId || undefined })
  })

  // Fetch hosts for filtering
  const { data: hostsData } = useQuery({
    queryKey: ['hosts', 'active'],
    queryFn: () => hostsApi.list({ active_only: true })
  })

  const hosts = hostsData?.items || []

  // Delete network mutation
  const deleteMutation = useMutation({
    mutationFn: ({ id, hostId }: { id: string; hostId?: string }) => 
      networksApi.delete(id, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networks'] })
      setSelectedNetworks(new Set())
    }
  })

  // Prune networks mutation
  const pruneMutation = useMutation({
    mutationFn: (hostId?: string) => networksApi.prune(undefined, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networks'] })
    }
  })

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedNetworks(new Set(networks.map(n => n.Id)))
    } else {
      setSelectedNetworks(new Set())
    }
  }

  const handleSelect = (networkId: string) => {
    const newSelected = new Set(selectedNetworks)
    if (newSelected.has(networkId)) {
      newSelected.delete(networkId)
    } else {
      newSelected.add(networkId)
    }
    setSelectedNetworks(newSelected)
  }

  const getHostInfo = (network: Network) => {
    if (!network.host_id) return null
    const host = hosts.find(h => h.id === network.host_id)
    return host
  }

  const getNetworkBadgeColor = (driver: string) => {
    switch (driver) {
      case 'bridge': return 'primary'
      case 'host': return 'warning'
      case 'none': return 'secondary'
      case 'overlay': return 'success'
      case 'macvlan': return 'info'
      default: return 'secondary'
    }
  }

  const formatSubnet = (ipam?: any) => {
    if (!ipam?.Config || ipam.Config.length === 0) return 'N/A'
    const config = ipam.Config[0]
    return config.Subnet || 'N/A'
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
        Error loading networks
      </div>
    )
  }

  return (
    <>
      <PageTitle 
        title="Networks" 
        breadcrumb={[
          { title: 'Resources', href: '#' },
          { title: 'Networks' }
        ]}
        actions={
          <div className="d-flex gap-2">
            <Link to="/networks/create" className="btn btn-primary">
              <i className="mdi mdi-plus-circle me-1"></i>
              Create Network
            </Link>
            <button 
              className="btn btn-danger"
              onClick={() => {
                if (confirm('Are you sure you want to remove all unused networks?')) {
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
      {hosts.length > 0 && (
        <div className="card mb-3">
          <div className="card-body">
            <div className="d-flex align-items-center gap-3">
              <label className="mb-0" htmlFor="hostFilter">Filter by host:</label>
              <select 
                id="hostFilter"
                className="form-select form-select-sm" 
                style={{ width: 'auto' }}
                value={hostId || ''}
                onChange={(e) => {
                  if (e.target.value) {
                    navigate(`/networks?host_id=${e.target.value}`)
                  } else {
                    navigate('/networks')
                  }
                }}
              >
                <option value="">All Hosts</option>
                {hosts.map(host => (
                  <option key={host.id} value={host.id}>
                    {host.display_name || host.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Networks Table */}
      <div className="card">
        <div className="card-body">
          {networks.length === 0 ? (
            <div className="text-center py-4 text-muted">
              <i className="mdi mdi-lan font-24 mb-3 d-block"></i>
              <p>No networks found</p>
              <Link to="/networks/create" className="btn btn-primary btn-sm">
                <i className="mdi mdi-plus-circle me-1"></i>
                Create Network
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
                        checked={selectedNetworks.size === networks.length && networks.length > 0}
                      />
                    </th>
                    <th>Name</th>
                    <th>Driver</th>
                    <th>Scope</th>
                    <th>Subnet</th>
                    <th>Containers</th>
                    {!hostId && <th>Host</th>}
                    <th>Properties</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {networks.map((network) => {
                    const host = getHostInfo(network)
                    const containerCount = Object.keys(network.Containers || {}).length
                    
                    return (
                      <tr key={`${network.host_id}-${network.Id}`}>
                        <td>
                          <input
                            type="checkbox"
                            className="form-check-input"
                            checked={selectedNetworks.has(network.Id)}
                            onChange={() => handleSelect(network.Id)}
                          />
                        </td>
                        <td>
                          <strong>{network.Name}</strong>
                          <div className="small text-muted text-truncate" style={{ maxWidth: '200px' }}>
                            {network.Id.substring(0, 12)}
                          </div>
                        </td>
                        <td>
                          <span className={`badge bg-soft-${getNetworkBadgeColor(network.Driver)} text-${getNetworkBadgeColor(network.Driver)}`}>
                            {network.Driver}
                          </span>
                        </td>
                        <td>
                          <span className={`badge bg-soft-${network.Scope === 'local' ? 'info' : 'primary'} text-${network.Scope === 'local' ? 'info' : 'primary'}`}>
                            {network.Scope}
                          </span>
                        </td>
                        <td>
                          <code className="small">{formatSubnet(network.IPAM)}</code>
                        </td>
                        <td>
                          {containerCount > 0 ? (
                            <span className="badge bg-soft-success text-success">
                              {containerCount} connected
                            </span>
                          ) : (
                            <span className="text-muted">None</span>
                          )}
                        </td>
                        {!hostId && (
                          <td>
                            {host ? (
                              <div className="d-flex align-items-center gap-2">
                                <HostHealthIndicator status={host.status} size="sm" />
                                <Link to={`/networks?host_id=${host.id}`}>
                                  {host.display_name || host.name}
                                </Link>
                              </div>
                            ) : (
                              <span className="text-muted">Unknown</span>
                            )}
                          </td>
                        )}
                        <td>
                          <div className="d-flex gap-2">
                            {network.Internal && (
                              <span className="badge bg-soft-warning text-warning" title="Internal network">
                                Internal
                              </span>
                            )}
                            {network.Attachable && (
                              <span className="badge bg-soft-info text-info" title="Attachable">
                                Attachable
                              </span>
                            )}
                            {network.Ingress && (
                              <span className="badge bg-soft-purple text-purple" title="Ingress network">
                                Ingress
                              </span>
                            )}
                            {network.EnableIPv6 && (
                              <span className="badge bg-soft-dark text-dark" title="IPv6 enabled">
                                IPv6
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          <div className="btn-group btn-group-sm">
                            <Link 
                              to={`/networks/${network.Id}?host_id=${network.host_id}`}
                              className="btn btn-soft-info"
                              title="View details"
                            >
                              <i className="mdi mdi-information-outline"></i>
                            </Link>
                            <button
                              className="btn btn-soft-danger"
                              title="Delete network"
                              onClick={() => {
                                if (confirm(`Are you sure you want to delete network "${network.Name}"?`)) {
                                  deleteMutation.mutate({ id: network.Id, hostId: network.host_id })
                                }
                              }}
                              disabled={deleteMutation.isPending || containerCount > 0}
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