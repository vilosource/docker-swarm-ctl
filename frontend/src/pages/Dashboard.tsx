import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import PageTitle from '@/components/common/PageTitle'
import { dashboardApi, DashboardData } from '@/api/dashboard'
import { HostHealthIndicator } from '@/components/common/HostHealthIndicator'

export default function Dashboard() {
  const { data: dashboard, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => dashboardApi.getDashboard(),
    refetchInterval: 30000 // Auto-refresh every 30 seconds
  })
  
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
        Error loading dashboard data
      </div>
    )
  }

  if (!dashboard) {
    return null
  }

  const hostStats = [
    { 
      label: 'Total Hosts', 
      value: dashboard.hosts.total, 
      icon: 'mdi mdi-server-network',
      color: 'primary' 
    },
    { 
      label: 'Healthy', 
      value: dashboard.hosts.healthy, 
      icon: 'mdi mdi-check-circle',
      color: 'success' 
    },
    { 
      label: 'Unhealthy', 
      value: dashboard.hosts.unhealthy + dashboard.hosts.unreachable, 
      icon: 'mdi mdi-alert-circle',
      color: 'danger' 
    },
    { 
      label: 'Pending', 
      value: dashboard.hosts.pending, 
      icon: 'mdi mdi-timer-sand',
      color: 'warning' 
    },
  ]

  const resourceStats = [
    { 
      label: 'Total Containers', 
      value: dashboard.resources.containers.total, 
      icon: 'mdi mdi-docker',
      color: 'info',
      detail: `${dashboard.resources.containers.running} running`
    },
    { 
      label: 'Images', 
      value: dashboard.resources.images.total, 
      icon: 'mdi mdi-layers',
      color: 'purple',
      detail: dashboard.resources.images.size > 0 
        ? `${(dashboard.resources.images.size / 1024 / 1024 / 1024).toFixed(2)} GB`
        : undefined
    },
    { 
      label: 'Volumes', 
      value: dashboard.resources.volumes.total, 
      icon: 'mdi mdi-database',
      color: 'orange',
      detail: dashboard.resources.volumes.size > 0
        ? `${(dashboard.resources.volumes.size / 1024 / 1024 / 1024).toFixed(2)} GB`
        : undefined
    },
    { 
      label: 'Networks', 
      value: dashboard.resources.networks.total, 
      icon: 'mdi mdi-lan',
      color: 'teal' 
    },
  ]

  const formatLastCheck = (lastCheck?: string) => {
    if (!lastCheck) return 'Never'
    const date = new Date(lastCheck)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return date.toLocaleDateString()
  }
  
  return (
    <>
      <PageTitle 
        title="Multi-Host Dashboard" 
        breadcrumb={[
          { title: 'Dashboard' }
        ]}
        actions={
          <button 
            className="btn btn-sm btn-soft-primary"
            onClick={() => refetch()}
          >
            <i className="mdi mdi-refresh me-1"></i>
            Refresh
          </button>
        }
      />
      
      {/* Host Overview Cards */}
      <h5 className="mb-3">Host Overview</h5>
      <div className="row">
        {hostStats.map((stat) => (
          <div key={stat.label} className="col-md-6 col-xl-3">
            <div className="card">
              <div className="card-body">
                <div className="d-flex">
                  <div className="flex-grow-1">
                    <span className="text-muted text-uppercase fs-12 fw-bold">{stat.label}</span>
                    <h3 className="mb-0">{stat.value}</h3>
                  </div>
                  <div className="align-self-center flex-shrink-0">
                    <div className={`avatar-sm rounded bg-soft-${stat.color}`}>
                      <i className={`${stat.icon} font-22 avatar-title text-${stat.color}`}></i>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Resource Stats Cards */}
      <h5 className="mb-3 mt-4">Aggregate Resources</h5>
      <div className="row">
        {resourceStats.map((stat) => (
          <div key={stat.label} className="col-md-6 col-xl-3">
            <div className="card">
              <div className="card-body">
                <div className="d-flex">
                  <div className="flex-grow-1">
                    <span className="text-muted text-uppercase fs-12 fw-bold">{stat.label}</span>
                    <h3 className="mb-0">{stat.value}</h3>
                    {stat.detail && (
                      <p className="text-muted mb-0 fs-13">{stat.detail}</p>
                    )}
                  </div>
                  <div className="align-self-center flex-shrink-0">
                    <i className={`${stat.icon} font-24 text-muted`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Host Details Table */}
      <div className="row mt-4">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <h4 className="header-title mb-0">Docker Hosts</h4>
            </div>
            <div className="card-body">
              {dashboard.host_details.length === 0 ? (
                <div className="text-center py-4 text-muted">
                  <i className="mdi mdi-server-network font-24 mb-3 d-block"></i>
                  <p>No Docker hosts configured</p>
                  <Link to="/hosts" className="btn btn-primary btn-sm">
                    <i className="mdi mdi-plus-circle me-1"></i>
                    Add Host
                  </Link>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover mb-0">
                    <thead>
                      <tr>
                        <th>Status</th>
                        <th>Name</th>
                        <th>Docker Version</th>
                        <th>Containers</th>
                        <th>Images</th>
                        <th>System</th>
                        <th>Last Check</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.host_details.map((host) => (
                        <tr key={host.id}>
                          <td>
                            <HostHealthIndicator status={host.status} size="md" />
                          </td>
                          <td>
                            <div>
                              <strong>{host.display_name || host.name}</strong>
                              {host.is_default && (
                                <span className="badge bg-soft-primary text-primary ms-2">Default</span>
                              )}
                              {host.display_name && (
                                <div className="text-muted small">{host.name}</div>
                              )}
                            </div>
                          </td>
                          <td>{host.stats.docker_version || 'N/A'}</td>
                          <td>
                            <div>
                              <span className="badge bg-soft-info text-info">
                                {host.stats.containers} total
                              </span>
                              {host.stats.containers_running > 0 && (
                                <span className="badge bg-soft-success text-success ms-1">
                                  {host.stats.containers_running} running
                                </span>
                              )}
                            </div>
                          </td>
                          <td>{host.stats.images}</td>
                          <td>
                            <div className="small text-muted">
                              {host.stats.os_type && <div>{host.stats.os_type}</div>}
                              {host.stats.cpu_count && <div>{host.stats.cpu_count} CPUs</div>}
                              {host.stats.memory_total && (
                                <div>{(host.stats.memory_total / 1024 / 1024 / 1024).toFixed(1)} GB RAM</div>
                              )}
                            </div>
                          </td>
                          <td>{formatLastCheck(host.last_health_check)}</td>
                          <td>
                            <div className="btn-group btn-group-sm">
                              <Link 
                                to={`/hosts/${host.id}/containers`} 
                                className="btn btn-soft-primary"
                                title="View containers"
                              >
                                <i className="mdi mdi-docker"></i>
                              </Link>
                              <Link 
                                to={`/hosts/${host.id}`} 
                                className="btn btn-soft-info"
                                title="Host details"
                              >
                                <i className="mdi mdi-information-outline"></i>
                              </Link>
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
    </>
  )
}