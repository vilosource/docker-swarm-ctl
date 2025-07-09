import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { api } from '@/api/client'

interface HostInfo {
  id: string
  display_name: string
  host_type?: string
  is_leader?: boolean
  url?: string
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
  swarm_spec?: any
  join_tokens?: {
    worker?: string
    manager?: string
  }
}

export default function SwarmClusterDetail() {
  const { swarmId } = useParams<{ swarmId: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('nodes')
  
  const { data: swarm, isLoading, error, refetch } = useQuery<SwarmClusterInfo>({
    queryKey: ['swarm', swarmId],
    queryFn: async () => {
      const response = await api.get(`/swarms/${swarmId}`)
      return response.data
    },
    enabled: !!swarmId
  })
  
  if (!swarmId) {
    return (
      <div className="alert alert-danger">
        No swarm ID provided
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
  
  if (error || !swarm) {
    return (
      <div className="row">
        <div className="col-12">
          <div className="alert alert-danger">
            Failed to load swarm details. Please try again.
          </div>
        </div>
      </div>
    )
  }
  
  const getNodeStatusBadge = (hostType: string | undefined) => {
    if (hostType === 'swarm_manager') {
      return <span className="badge bg-primary">Manager</span>
    } else if (hostType === 'swarm_worker') {
      return <span className="badge bg-info">Worker</span>
    }
    return <span className="badge bg-secondary">Unknown</span>
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
                onClick={() => navigate('/swarms')}
              >
                <i className="mdi mdi-arrow-left me-1"></i>
                Back to Clusters
              </button>
              <button
                className="btn btn-primary"
                onClick={() => refetch()}
                title="Refresh"
              >
                <i className="mdi mdi-refresh"></i>
              </button>
            </div>
            <h4 className="page-title">
              <i className="mdi mdi-cloud-braces me-2"></i>
              {swarm.cluster_name}
            </h4>
          </div>
        </div>
      </div>
      
      {/* Swarm Info Cards */}
      <div className="row">
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-server-network text-primary" style={{ fontSize: '2rem' }}></i>
                <h3 className="mb-1">{swarm.total_nodes}</h3>
                <p className="text-muted mb-0">Total Nodes</p>
                <small className="text-muted">{swarm.manager_count}M, {swarm.worker_count}W</small>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-check-network text-success" style={{ fontSize: '2rem' }}></i>
                <h3 className="mb-1">{swarm.ready_nodes}</h3>
                <p className="text-muted mb-0">Ready Nodes</p>
                <small className="text-muted">
                  {swarm.total_nodes > 0 ? ((swarm.ready_nodes / swarm.total_nodes) * 100).toFixed(0) : 0}% Available
                </small>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-apps text-info" style={{ fontSize: '2rem' }}></i>
                <h3 className="mb-1">{swarm.service_count}</h3>
                <p className="text-muted mb-0">Services</p>
                <small className="text-muted">Running</small>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-crown text-warning" style={{ fontSize: '2rem' }}></i>
                <h5 className="mb-1">{swarm.leader_host.display_name}</h5>
                <p className="text-muted mb-0">Leader</p>
                <small className="text-muted">Primary Manager</small>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <ul className="nav nav-tabs nav-bordered">
                <li className="nav-item">
                  <a
                    className={`nav-link ${activeTab === 'nodes' ? 'active' : ''}`}
                    onClick={() => setActiveTab('nodes')}
                    style={{ cursor: 'pointer' }}
                  >
                    <i className="mdi mdi-server-network me-1"></i>
                    Nodes ({swarm.total_nodes})
                  </a>
                </li>
                <li className="nav-item">
                  <a
                    className={`nav-link ${activeTab === 'services' ? 'active' : ''}`}
                    onClick={() => setActiveTab('services')}
                    style={{ cursor: 'pointer' }}
                  >
                    <i className="mdi mdi-apps me-1"></i>
                    Services ({swarm.service_count})
                  </a>
                </li>
                <li className="nav-item">
                  <a
                    className={`nav-link ${activeTab === 'tokens' ? 'active' : ''}`}
                    onClick={() => setActiveTab('tokens')}
                    style={{ cursor: 'pointer' }}
                  >
                    <i className="mdi mdi-key me-1"></i>
                    Join Tokens
                  </a>
                </li>
              </ul>
              
              <div className="tab-content">
                {/* Nodes Tab */}
                {activeTab === 'nodes' && (
                  <div className="tab-pane show active">
                    <h5 className="mt-3 mb-3">Swarm Nodes</h5>
                    <div className="table-responsive">
                      <table className="table table-hover mb-0">
                        <thead>
                          <tr>
                            <th>Node Name</th>
                            <th>Role</th>
                            <th>Status</th>
                            <th>IP Address</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {swarm.hosts.map((host) => (
                            <tr key={host.id}>
                              <td>
                                <strong>{host.display_name}</strong>
                                {host.is_leader && (
                                  <span className="badge bg-warning ms-2">
                                    <i className="mdi mdi-crown me-1"></i>
                                    Leader
                                  </span>
                                )}
                              </td>
                              <td>{getNodeStatusBadge(host.host_type)}</td>
                              <td>
                                <span className="badge bg-success">Ready</span>
                              </td>
                              <td>
                                <code className="text-muted">
                                  {host.url ? host.url.split('://')[1].split(':')[0] : 'N/A'}
                                </code>
                              </td>
                              <td>
                                <div className="btn-group btn-group-sm">
                                  <Link
                                    to={`/hosts/${host.id}/nodes`}
                                    className="btn btn-light"
                                    title="Manage Nodes"
                                  >
                                    <i className="mdi mdi-cog"></i>
                                  </Link>
                                  <Link
                                    to={`/hosts/${host.id}/containers`}
                                    className="btn btn-light"
                                    title="View Containers"
                                  >
                                    <i className="mdi mdi-docker"></i>
                                  </Link>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {/* Services Tab */}
                {activeTab === 'services' && (
                  <div className="tab-pane show active">
                    <h5 className="mt-3 mb-3">Swarm Services</h5>
                    {swarm.service_count === 0 ? (
                      <div className="text-center py-4">
                        <i className="mdi mdi-apps" style={{ fontSize: '3rem', color: '#6c757d' }}></i>
                        <p className="text-muted mt-2">No services running in this swarm</p>
                        <Link
                          to={`/hosts/${swarm.leader_host.id}/services`}
                          className="btn btn-primary btn-sm"
                        >
                          <i className="mdi mdi-plus me-1"></i>
                          Create Service
                        </Link>
                        <p className="text-muted mt-3">
                          <small>Services must be managed through a manager node</small>
                        </p>
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-muted mb-3">
                          This swarm has {swarm.service_count} service{swarm.service_count !== 1 ? 's' : ''} running
                        </p>
                        <Link
                          to={`/hosts/${swarm.leader_host.id}/services`}
                          className="btn btn-primary"
                        >
                          <i className="mdi mdi-eye me-1"></i>
                          Manage Services
                        </Link>
                        <p className="text-muted mt-3">
                          <small>Services are managed through the swarm leader node</small>
                        </p>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Join Tokens Tab */}
                {activeTab === 'tokens' && (
                  <div className="tab-pane show active">
                    <h5 className="mt-3 mb-3">Join Tokens</h5>
                    <div className="alert alert-info">
                      <i className="mdi mdi-information me-1"></i>
                      Use these tokens to join additional nodes to this swarm cluster.
                    </div>
                    
                    <div className="row">
                      <div className="col-md-6">
                        <div className="card">
                          <div className="card-body">
                            <h5 className="card-title">
                              <i className="mdi mdi-worker me-1"></i>
                              Worker Token
                            </h5>
                            <p className="text-muted">Use this token to join a node as a worker</p>
                            <code className="d-block p-2 bg-light">
                              {swarm.join_tokens?.worker || 'Token not available'}
                            </code>
                          </div>
                        </div>
                      </div>
                      <div className="col-md-6">
                        <div className="card">
                          <div className="card-body">
                            <h5 className="card-title">
                              <i className="mdi mdi-shield-crown me-1"></i>
                              Manager Token
                            </h5>
                            <p className="text-muted">Use this token to join a node as a manager</p>
                            <code className="d-block p-2 bg-light">
                              {swarm.join_tokens?.manager || 'Token not available'}
                            </code>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Swarm Details */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">Swarm Details</h5>
              <div className="row">
                <div className="col-md-6">
                  <p><strong>Swarm ID:</strong> <code>{swarm.swarm_id}</code></p>
                  <p><strong>Created:</strong> {swarm.created_at 
                    ? formatDistanceToNow(new Date(swarm.created_at), { addSuffix: true })
                    : 'Unknown'}</p>
                </div>
                <div className="col-md-6">
                  <p><strong>Cluster Name:</strong> {swarm.cluster_name}</p>
                  <p><strong>Last Updated:</strong> {swarm.updated_at 
                    ? formatDistanceToNow(new Date(swarm.updated_at), { addSuffix: true })
                    : 'Unknown'}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}