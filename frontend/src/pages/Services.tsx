import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useServices, useScaleService, useRemoveService } from '../hooks/useServices'
import { formatDistanceToNow } from 'date-fns'

export default function Services() {
  const { hostId } = useParams<{ hostId: string }>()
  const navigate = useNavigate()
  const [selectedService, setSelectedService] = useState<any>(null)
  const [showScaleModal, setShowScaleModal] = useState(false)
  const [showRemoveModal, setShowRemoveModal] = useState(false)
  const [replicas, setReplicas] = useState<number>(1)

  const { data, isLoading, error, refetch } = useServices(hostId || '')
  const scaleService = useScaleService()
  const removeService = useRemoveService()

  const handleScaleClick = (service: any) => {
    setSelectedService(service)
    setReplicas(service.replicas || 1)
    setShowScaleModal(true)
  }

  const handleRemoveClick = (service: any) => {
    setSelectedService(service)
    setShowRemoveModal(true)
  }

  const handleScale = async () => {
    if (!hostId || !selectedService) return

    try {
      await scaleService.mutateAsync({
        hostId,
        serviceId: selectedService.ID,
        replicas,
      })
      setShowScaleModal(false)
      setSelectedService(null)
    } catch (error) {
      console.error('Failed to scale service:', error)
    }
  }

  const handleRemove = async () => {
    if (!hostId || !selectedService) return

    try {
      await removeService.mutateAsync({
        hostId,
        serviceId: selectedService.ID,
      })
      setShowRemoveModal(false)
      setSelectedService(null)
    } catch (error) {
      console.error('Failed to remove service:', error)
    }
  }

  const getStatusBadge = (service: any) => {
    if (service.UpdateStatus?.State === 'updating') {
      return <span className="badge bg-warning">Updating</span>
    }
    if (service.UpdateStatus?.State === 'paused') {
      return <span className="badge bg-secondary">Paused</span>
    }
    return <span className="badge bg-success">Running</span>
  }

  const getReplicaStatus = (service: any) => {
    if (service.mode !== 'replicated') {
      return <span className="badge bg-info">Global</span>
    }
    
    const running = service.runningTasks || 0
    const desired = service.replicas || 0
    
    return (
      <div className="d-flex align-items-center">
        <span>{running}/{desired}</span>
        {running < desired && (
          <div className="spinner-border spinner-border-sm ms-2" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        )}
      </div>
    )
  }

  const getServicePorts = (service: any) => {
    const ports = service.Endpoint?.Ports || []
    if (ports.length === 0) return '-'
    
    return ports.map((port: any) => (
      <span
        key={`${port.TargetPort}-${port.PublishedPort}`}
        className="badge bg-light text-dark me-1"
      >
        {port.PublishedPort || '?'}:{port.TargetPort}/{port.Protocol}
      </span>
    ))
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
            Failed to load services: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </div>
      </div>
    )
  }

  const services = data?.services || []

  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              <button
                className="btn btn-secondary me-2"
                onClick={() => refetch()}
              >
                <i className="mdi mdi-refresh me-1"></i>
                Refresh
              </button>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/hosts/${hostId}/services/create`)}
              >
                <i className="mdi mdi-plus me-1"></i>
                Create Service
              </button>
            </div>
            <h4 className="page-title">
              <i className="mdi mdi-apps me-2"></i>
              Services
            </h4>
          </div>
        </div>
      </div>

      {/* Services Table */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              {services.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-muted mb-0">No services running</p>
                  <button
                    className="btn btn-sm btn-primary mt-2"
                    onClick={() => navigate(`/hosts/${hostId}/services/create`)}
                  >
                    Create your first service
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover mb-0">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Image</th>
                        <th>Mode</th>
                        <th>Replicas</th>
                        <th>Ports</th>
                        <th>Status</th>
                        <th>Updated</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {services.map((service) => (
                        <tr key={service.ID}>
                          <td>
                            <strong>{service.name}</strong>
                          </td>
                          <td>
                            <code className="text-muted">{service.image}</code>
                          </td>
                          <td>
                            <span className="text-capitalize">{service.mode}</span>
                          </td>
                          <td>{getReplicaStatus(service)}</td>
                          <td>{getServicePorts(service)}</td>
                          <td>{getStatusBadge(service)}</td>
                          <td>
                            {service.UpdatedAt && 
                              <small>{formatDistanceToNow(new Date(service.UpdatedAt), { addSuffix: true })}</small>
                            }
                          </td>
                          <td>
                            <div className="btn-group btn-group-sm">
                              {service.mode === 'replicated' && (
                                <button
                                  className="btn btn-light"
                                  onClick={() => handleScaleClick(service)}
                                  title="Scale Service"
                                >
                                  <i className="mdi mdi-scale-balance"></i>
                                </button>
                              )}
                              <button
                                className="btn btn-light"
                                onClick={() => navigate(`/hosts/${hostId}/services/${service.ID}/logs`)}
                                title="View Logs"
                              >
                                <i className="mdi mdi-file-document-outline"></i>
                              </button>
                              <button
                                className="btn btn-light"
                                onClick={() => navigate(`/hosts/${hostId}/services/${service.ID}/tasks`)}
                                title="View Tasks"
                              >
                                <i className="mdi mdi-format-list-bulleted"></i>
                              </button>
                              <button
                                className="btn btn-light"
                                onClick={() => navigate(`/hosts/${hostId}/services/${service.ID}/edit`)}
                                title="Edit Service"
                              >
                                <i className="mdi mdi-pencil"></i>
                              </button>
                              <button
                                className="btn btn-light text-danger"
                                onClick={() => handleRemoveClick(service)}
                                title="Remove Service"
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

      {/* Scale Service Modal */}
      {showScaleModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Scale Service</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowScaleModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-info">
                  Scaling will gradually update the service to the desired number of replicas.
                </div>
                <div className="mb-3">
                  <label className="form-label">Number of Replicas</label>
                  <input
                    type="number"
                    className="form-control"
                    value={replicas}
                    onChange={(e) => setReplicas(parseInt(e.target.value) || 0)}
                    min="0"
                    max="100"
                  />
                  <small className="text-muted">
                    Current: {selectedService?.replicas || 0} replicas
                  </small>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowScaleModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleScale}
                  disabled={scaleService.isPending}
                >
                  {scaleService.isPending ? 'Scaling...' : 'Scale'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Remove Service Modal */}
      {showRemoveModal && (
        <div className="modal show d-block" tabIndex={-1}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Remove Service</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowRemoveModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-warning">
                  This will permanently remove the service and stop all its tasks.
                </div>
                <p>
                  Are you sure you want to remove service <strong>{selectedService?.name}</strong>?
                </p>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowRemoveModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={handleRemove}
                  disabled={removeService.isPending}
                >
                  {removeService.isPending ? 'Removing...' : 'Remove'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Backdrop */}
      {(showScaleModal || showRemoveModal) && (
        <div className="modal-backdrop fade show"></div>
      )}
    </>
  )
}