import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSwarmInfo, useSwarmInit, useSwarmLeave } from '../hooks/useSwarm'
import { useNodes } from '../hooks/useNodes'
import { useServices } from '../hooks/useServices'
import { formatDistanceToNow } from 'date-fns'

export default function SwarmOverview() {
  const { hostId } = useParams<{ hostId: string }>()
  const navigate = useNavigate()
  const [showInitModal, setShowInitModal] = useState(false)
  const [showLeaveModal, setShowLeaveModal] = useState(false)
  const [advertiseAddr, setAdvertiseAddr] = useState('')
  
  const { data: swarmInfo, isLoading: swarmLoading, error: swarmError } = useSwarmInfo(hostId || '')
  const { data: nodesData, isLoading: nodesLoading } = useNodes(hostId || '')
  const { data: servicesData, isLoading: servicesLoading } = useServices(hostId || '')
  
  const swarmInit = useSwarmInit()
  const swarmLeave = useSwarmLeave()
  
  const isNotInSwarm = swarmError && 'response' in swarmError && swarmError.response?.status === 400
  
  const handleInitSwarm = async () => {
    if (!hostId || !advertiseAddr) return
    
    try {
      await swarmInit.mutateAsync({
        hostId,
        data: { advertise_addr: advertiseAddr }
      })
      setShowInitModal(false)
      setAdvertiseAddr('')
    } catch (error) {
      console.error('Failed to initialize swarm:', error)
    }
  }
  
  const handleLeaveSwarm = async (force: boolean) => {
    if (!hostId) return
    
    try {
      await swarmLeave.mutateAsync({ hostId, force })
      setShowLeaveModal(false)
    } catch (error) {
      console.error('Failed to leave swarm:', error)
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
  
  if (swarmLoading || nodesLoading || servicesLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }
  
  const nodes = nodesData?.nodes || []
  const services = servicesData?.services || []
  const managerNodes = nodes.filter(n => n.role === 'manager')
  const workerNodes = nodes.filter(n => n.role === 'worker')
  const readyNodes = nodes.filter(n => n.state === 'ready')
  const runningServices = services.filter(s => s.UpdateStatus?.State !== 'paused')
  
  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              {!isNotInSwarm && (
                <button
                  className="btn btn-secondary"
                  onClick={() => window.location.reload()}
                  title="Refresh"
                >
                  <i className="mdi mdi-refresh"></i>
                </button>
              )}
            </div>
            <h4 className="page-title">
              <i className="mdi mdi-cloud me-2"></i>
              Docker Swarm
            </h4>
          </div>
        </div>
      </div>
      
      {isNotInSwarm ? (
        <div className="row">
          <div className="col-12">
            <div className="card">
              <div className="card-body">
                <div className="alert alert-info">
                  <h5 className="alert-heading">Not Part of a Swarm</h5>
                  <p className="mb-0">This Docker host is not currently part of a swarm cluster.</p>
                </div>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-primary"
                    onClick={() => setShowInitModal(true)}
                  >
                    <i className="mdi mdi-plus me-1"></i>
                    Initialize New Swarm
                  </button>
                  <button
                    className="btn btn-outline-primary"
                    onClick={() => navigate(`/hosts/${hostId}/join-swarm`)}
                  >
                    Join Existing Swarm
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Swarm Info Card */}
          <div className="row">
            <div className="col-12">
              <div className="card">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="card-title mb-0">Swarm Information</h5>
                    <div>
                      <button
                        className="btn btn-sm btn-light me-1"
                        onClick={() => navigate(`/swarm/${hostId}/tokens`)}
                        title="Manage Tokens"
                      >
                        <i className="mdi mdi-key"></i>
                      </button>
                      <button
                        className="btn btn-sm btn-light me-1"
                        onClick={() => navigate(`/swarm/${hostId}/settings`)}
                        title="Swarm Settings"
                      >
                        <i className="mdi mdi-cog"></i>
                      </button>
                      <button
                        className="btn btn-sm btn-light text-danger"
                        onClick={() => setShowLeaveModal(true)}
                        title="Leave Swarm"
                      >
                        <i className="mdi mdi-exit-to-app"></i>
                      </button>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-md-6">
                      <p className="text-muted mb-1">Swarm ID</p>
                      <p className="font-monospace">{swarmInfo?.ID}</p>
                    </div>
                    <div className="col-md-6">
                      <p className="text-muted mb-1">Created</p>
                      <p>
                        {swarmInfo?.CreatedAt && formatDistanceToNow(new Date(swarmInfo.CreatedAt), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Stats Grid */}
          <div className="row">
            <div className="col-sm-6 col-lg-3">
              <div className="card">
                <div className="card-body text-center">
                  <i className="mdi mdi-server-network text-primary" style={{ fontSize: '3rem' }}></i>
                  <h3 className="mb-1">{nodes.length}</h3>
                  <p className="text-muted mb-2">Total Nodes</p>
                  <div>
                    <span className="badge bg-light text-dark me-1">{managerNodes.length} Managers</span>
                    <span className="badge bg-light text-dark">{workerNodes.length} Workers</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="col-sm-6 col-lg-3">
              <div className="card">
                <div className="card-body text-center">
                  <i className="mdi mdi-server-network text-success" style={{ fontSize: '3rem' }}></i>
                  <h3 className="mb-1">{readyNodes.length}</h3>
                  <p className="text-muted mb-2">Ready Nodes</p>
                  <p className="mb-0">
                    {nodes.length > 0 ? ((readyNodes.length / nodes.length) * 100).toFixed(0) : 0}% Healthy
                  </p>
                </div>
              </div>
            </div>
            
            <div className="col-sm-6 col-lg-3">
              <div className="card">
                <div className="card-body text-center">
                  <i className="mdi mdi-apps text-info" style={{ fontSize: '3rem' }}></i>
                  <h3 className="mb-1">{services.length}</h3>
                  <p className="text-muted mb-2">Services</p>
                  <p className="mb-0">{runningServices.length} Running</p>
                </div>
              </div>
            </div>
            
            <div className="col-sm-6 col-lg-3">
              <div className="card">
                <div className="card-body text-center">
                  <i className="mdi mdi-security text-warning" style={{ fontSize: '3rem' }}></i>
                  <h3 className="mb-1">TLS</h3>
                  <p className="text-muted mb-2">Security</p>
                  <p className="mb-0 text-success">Enabled</p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Quick Actions */}
          <div className="row">
            <div className="col-12">
              <div className="card">
                <div className="card-body">
                  <h5 className="card-title">Quick Actions</h5>
                  <div className="d-flex flex-wrap gap-2">
                    <button
                      className="btn btn-primary"
                      onClick={() => navigate(`/hosts/${hostId}/services/create`)}
                    >
                      <i className="mdi mdi-apps me-1"></i>
                      Create Service
                    </button>
                    <button
                      className="btn btn-outline-primary"
                      onClick={() => navigate(`/hosts/${hostId}/nodes`)}
                    >
                      <i className="mdi mdi-server-network me-1"></i>
                      Manage Nodes
                    </button>
                    <button
                      className="btn btn-outline-primary"
                      onClick={() => navigate(`/hosts/${hostId}/services`)}
                    >
                      View Services
                    </button>
                    <button
                      className="btn btn-outline-primary"
                      onClick={() => navigate(`/hosts/${hostId}/secrets-configs`)}
                    >
                      Secrets & Configs
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
      
      {/* Initialize Swarm Modal */}
      {showInitModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Initialize Docker Swarm</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowInitModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-warning">
                  This will initialize a new swarm with this host as the first manager node.
                </div>
                <div className="mb-3">
                  <label className="form-label">Advertise Address</label>
                  <input
                    type="text"
                    className="form-control"
                    value={advertiseAddr}
                    onChange={(e) => setAdvertiseAddr(e.target.value)}
                    placeholder="e.g., 192.168.1.100:2377"
                  />
                  <small className="text-muted">
                    The address that will be advertised to other nodes for API access
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowInitModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleInitSwarm}
                  disabled={!advertiseAddr || swarmInit.isPending}
                >
                  {swarmInit.isPending ? 'Initializing...' : 'Initialize Swarm'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Leave Swarm Modal */}
      {showLeaveModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Leave Swarm</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowLeaveModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-danger">
                  <h5 className="alert-heading">Warning</h5>
                  <p className="mb-0">
                    Leaving the swarm will remove this node from the cluster. Services running on this node will be rescheduled to other nodes.
                  </p>
                </div>
                <p>Are you sure you want to leave the swarm?</p>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowLeaveModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-warning"
                  onClick={() => handleLeaveSwarm(false)}
                  disabled={swarmLeave.isPending}
                >
                  Leave Swarm
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => handleLeaveSwarm(true)}
                  disabled={swarmLeave.isPending}
                >
                  Force Leave
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Backdrop */}
      {(showInitModal || showLeaveModal) && (
        <div className="modal-backdrop fade show"></div>
      )}
    </>
  )
}