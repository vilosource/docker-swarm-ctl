import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { api } from '@/api/client'

interface HostInfo {
  id: string
  display_name: string
  host_type?: string
  is_leader?: boolean
}

interface SwarmClusterInfo {
  swarm_id: string
  cluster_name: string
  created_at?: string
  updated_at?: string
  manager_count: number
  worker_count: number
  total_nodes: number
  ready_nodes: number
  service_count: number
  leader_host: HostInfo
  hosts: HostInfo[]
}

interface SwarmClustersResponse {
  swarms: SwarmClusterInfo[]
  total: number
}

export default function SwarmClustersOverview() {
  const navigate = useNavigate()
  
  const { data, isLoading, error, refetch } = useQuery<SwarmClustersResponse>({
    queryKey: ['swarms'],
    queryFn: async () => {
      const response = await api.get('/swarms/')
      return response.data
    }
  })
  
  const getHealthStatus = (cluster: SwarmClusterInfo) => {
    // Simple health check based on ready nodes
    if (cluster.ready_nodes === cluster.total_nodes) {
      return { status: 'Healthy', color: 'success', icon: 'check-circle' }
    } else if (cluster.ready_nodes >= cluster.total_nodes * 0.5) {
      return { status: 'Degraded', color: 'warning', icon: 'alert' }
    } else {
      return { status: 'Critical', color: 'danger', icon: 'alert-circle' }
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
      <div className="row">
        <div className="col-12">
          <div className="alert alert-danger">
            Failed to load swarm clusters. Please try again.
          </div>
        </div>
      </div>
    )
  }
  
  const swarms = data?.swarms || []
  
  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              <button
                className="btn btn-secondary"
                onClick={() => refetch()}
                title="Refresh"
              >
                <i className="mdi mdi-refresh"></i>
              </button>
            </div>
            <h4 className="page-title">
              <i className="mdi mdi-cloud-braces me-2"></i>
              Swarm Clusters Overview
            </h4>
          </div>
        </div>
      </div>
      
      {swarms.length === 0 ? (
        <div className="row">
          <div className="col-12">
            <div className="card">
              <div className="card-body text-center py-5">
                <i className="mdi mdi-cloud-off-outline" style={{ fontSize: '3rem', color: '#6c757d' }}></i>
                <h5 className="mt-3">No Swarm Clusters Found</h5>
                <p className="text-muted">
                  No Docker hosts are currently part of a swarm cluster.
                </p>
                <button
                  className="btn btn-primary"
                  onClick={() => navigate('/hosts')}
                >
                  <i className="mdi mdi-server me-1"></i>
                  Go to Hosts
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Swarm Clusters Grid */}
          <div className="row">
            {swarms.map((swarm) => {
              const health = getHealthStatus(swarm)
              
              return (
                <div key={swarm.swarm_id} className="col-lg-4 col-md-6">
                  <div 
                    className="card cursor-pointer" 
                    onClick={() => navigate(`/swarms/${swarm.swarm_id}`)}
                    style={{ cursor: 'pointer' }}
                    title="Click to view nodes, services, and configurations for this swarm"
                  >
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-start mb-3">
                        <div>
                          <h5 className="card-title mb-1">{swarm.cluster_name}</h5>
                          <p className="text-muted small mb-0">ID: {swarm.swarm_id.substring(0, 12)}</p>
                        </div>
                        <span className={`badge bg-${health.color}`}>
                          <i className={`mdi mdi-${health.icon} me-1`}></i>
                          {health.status}
                        </span>
                      </div>
                      
                      <div className="row text-center mb-3">
                        <div className="col-4">
                          <div>
                            <i className="mdi mdi-server-network text-primary" style={{ fontSize: '2rem' }}></i>
                            <h4 className="mb-0">{swarm.total_nodes}</h4>
                            <p className="text-muted mb-0">Nodes</p>
                            <small className="text-muted">{swarm.manager_count}M, {swarm.worker_count}W</small>
                          </div>
                        </div>
                        <div className="col-4">
                          <div>
                            <i className="mdi mdi-apps text-info" style={{ fontSize: '2rem' }}></i>
                            <h4 className="mb-0">{swarm.service_count}</h4>
                            <p className="text-muted mb-0">Services</p>
                            <small className="text-muted">
                              {swarm.service_count > 0 ? 'Running' : 'No services'}
                            </small>
                          </div>
                        </div>
                        <div className="col-4">
                          <div>
                            <i className="mdi mdi-check-network text-success" style={{ fontSize: '2rem' }}></i>
                            <h4 className="mb-0">{swarm.ready_nodes}</h4>
                            <p className="text-muted mb-0">Ready</p>
                            <small className="text-muted">
                              {((swarm.ready_nodes / swarm.total_nodes) * 100).toFixed(0)}%
                            </small>
                          </div>
                        </div>
                      </div>
                      
                      <div className="border-top pt-3">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <small className="text-muted d-block">Leader</small>
                            <span className="font-weight-medium">{swarm.leader_host.display_name}</span>
                          </div>
                          <div className="text-end">
                            <small className="text-muted d-block">Created</small>
                            <span className="font-weight-medium">
                              {swarm.created_at 
                                ? formatDistanceToNow(new Date(swarm.created_at), { addSuffix: true })
                                : 'Unknown'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          
          {/* Quick Stats */}
          <div className="row mt-3">
            <div className="col-12">
              <div className="card">
                <div className="card-body">
                  <h5 className="card-title mb-3">Summary</h5>
                  <div className="row">
                    <div className="col-md-3">
                      <div className="text-center">
                        <h3 className="mb-1">{swarms.length}</h3>
                        <p className="text-muted mb-0">Total Swarm Clusters</p>
                      </div>
                    </div>
                    <div className="col-md-3">
                      <div className="text-center">
                        <h3 className="mb-1">
                          {swarms.reduce((acc, s) => acc + s.total_nodes, 0)}
                        </h3>
                        <p className="text-muted mb-0">Total Nodes</p>
                      </div>
                    </div>
                    <div className="col-md-3">
                      <div className="text-center">
                        <h3 className="mb-1">
                          {swarms.reduce((acc, s) => acc + s.service_count, 0)}
                        </h3>
                        <p className="text-muted mb-0">Total Services</p>
                      </div>
                    </div>
                    <div className="col-md-3">
                      <div className="text-center">
                        <h3 className="mb-1">
                          {swarms.filter(s => getHealthStatus(s).status === 'Healthy').length}
                        </h3>
                        <p className="text-muted mb-0">Healthy Clusters</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}