import { useEffect } from 'react'
import { useHostStore } from '@/store/hostStore'
import { HostStatus } from '@/types'

export default function HostSelector() {
  const { hosts, currentHostId, loading, fetchHosts, selectHost } = useHostStore()
  
  useEffect(() => {
    // Fetch hosts on mount
    fetchHosts()
  }, [])
  
  const currentHost = hosts.find(h => h.id === currentHostId)
  
  const getStatusIcon = (status: HostStatus) => {
    switch (status) {
      case 'healthy':
        return <i className="mdi mdi-check-circle text-success"></i>
      case 'unhealthy':
        return <i className="mdi mdi-alert-circle text-danger"></i>
      case 'pending':
        return <i className="mdi mdi-clock-outline text-warning"></i>
      case 'unreachable':
        return <i className="mdi mdi-lan-disconnect text-muted"></i>
      default:
        return <i className="mdi mdi-help-circle text-muted"></i>
    }
  }
  
  const getHostTypeLabel = (host: typeof hosts[0]) => {
    if (host.host_type === 'swarm_manager') {
      return host.is_leader ? 'Swarm Leader' : 'Swarm Manager'
    } else if (host.host_type === 'swarm_worker') {
      return 'Swarm Worker'
    }
    return 'Standalone'
  }
  
  if (loading && hosts.length === 0) {
    return (
      <div className="host-selector">
        <span className="text-muted">Loading hosts...</span>
      </div>
    )
  }
  
  if (hosts.length === 0) {
    return (
      <div className="host-selector">
        <span className="text-muted">No hosts available</span>
      </div>
    )
  }
  
  return (
    <div className="dropdown host-selector">
      <button
        className="btn btn-sm btn-outline-secondary dropdown-toggle d-flex align-items-center"
        type="button"
        data-bs-toggle="dropdown"
        aria-expanded="false"
      >
        {currentHost ? (
          <>
            {getStatusIcon(currentHost.status)}
            <span className="ms-2">{currentHost.name}</span>
          </>
        ) : (
          <span>Select Host</span>
        )}
      </button>
      
      <ul className="dropdown-menu dropdown-menu-end" style={{ maxHeight: '400px', overflowY: 'auto' }}>
        <li>
          <h6 className="dropdown-header">Docker Hosts</h6>
        </li>
        {hosts.map(host => (
          <li key={host.id}>
            <button
              className={`dropdown-item d-flex align-items-center ${host.id === currentHostId ? 'active' : ''}`}
              onClick={() => selectHost(host.id)}
              disabled={!host.is_active}
            >
              <div className="d-flex align-items-start w-100">
                <div className="me-2 mt-1">
                  {getStatusIcon(host.status)}
                </div>
                <div className="flex-grow-1">
                  <div className="fw-medium">{host.name}</div>
                  <small className="text-muted d-block">
                    {getHostTypeLabel(host)}
                    {host.cluster_name && ` • ${host.cluster_name}`}
                  </small>
                  {host.description && (
                    <small className="text-muted d-block">{host.description}</small>
                  )}
                </div>
                {host.is_default && (
                  <span className="badge bg-primary ms-2">Default</span>
                )}
              </div>
            </button>
          </li>
        ))}
        
        <li><hr className="dropdown-divider" /></li>
        <li>
          <a className="dropdown-item" href="/hosts">
            <i className="mdi mdi-cog me-2"></i>
            Manage Hosts
          </a>
        </li>
      </ul>
    </div>
  )
}