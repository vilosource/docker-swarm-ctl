import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useService, useServiceTasks, useScaleService, useRemoveService } from '../hooks/useServices'
import { formatDistanceToNow } from 'date-fns'
import ServiceLogViewer from '../components/logs/ServiceLogViewer'

export default function ServiceDetail() {
  const { hostId, serviceId } = useParams<{ hostId: string; serviceId: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [showScaleModal, setShowScaleModal] = useState(false)
  const [showRemoveModal, setShowRemoveModal] = useState(false)
  const [replicas, setReplicas] = useState<number>(1)

  const { data: service, isLoading, error, refetch } = useService(hostId || '', serviceId || '')
  const { data: tasksData } = useServiceTasks(hostId || '', serviceId || '')
  const scaleService = useScaleService()
  const removeService = useRemoveService()

  const handleScaleClick = () => {
    if (service) {
      setReplicas(service.replicas || 1)
      setShowScaleModal(true)
    }
  }

  const handleScale = async () => {
    if (!hostId || !serviceId) return

    try {
      await scaleService.mutateAsync({
        hostId,
        serviceId,
        replicas,
      })
      setShowScaleModal(false)
      refetch()
    } catch (error) {
      console.error('Failed to scale service:', error)
    }
  }

  const handleRemove = async () => {
    if (!hostId || !serviceId) return

    try {
      await removeService.mutateAsync({
        hostId,
        serviceId,
      })
      navigate(`/hosts/${hostId}/services`)
    } catch (error) {
      console.error('Failed to remove service:', error)
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

  if (error || !service) {
    return (
      <div className="row">
        <div className="col-12">
          <div className="alert alert-danger">
            Failed to load service details. Please try again.
          </div>
        </div>
      </div>
    )
  }

  const tasks = tasksData?.tasks || []
  const runningTasks = tasks.filter(task => task.Status.State === 'running').length

  return (
    <>
      {/* Page Title */}
      <div className="row">
        <div className="col-12">
          <div className="page-title-box">
            <div className="page-title-right">
              <button
                className="btn btn-secondary me-2"
                onClick={() => navigate(`/hosts/${hostId}/services`)}
              >
                <i className="mdi mdi-arrow-left me-1"></i>
                Back to Services
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
              <i className="mdi mdi-apps me-2"></i>
              {service.name}
            </h4>
          </div>
        </div>
      </div>

      {/* Service Info Cards */}
      <div className="row">
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-docker text-primary" style={{ fontSize: '2rem' }}></i>
                <h5 className="mb-1">{service.image}</h5>
                <p className="text-muted mb-0">Image</p>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-format-list-numbered text-info" style={{ fontSize: '2rem' }}></i>
                <h3 className="mb-1">{runningTasks}/{service.replicas || 0}</h3>
                <p className="text-muted mb-0">Tasks</p>
                <small className="text-muted">Running/Desired</small>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-cog text-warning" style={{ fontSize: '2rem' }}></i>
                <h5 className="mb-1">{service.mode}</h5>
                <p className="text-muted mb-0">Mode</p>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3 col-sm-6">
          <div className="card">
            <div className="card-body">
              <div className="text-center">
                <i className="mdi mdi-calendar text-success" style={{ fontSize: '2rem' }}></i>
                <h6 className="mb-1">
                  {formatDistanceToNow(new Date(service.CreatedAt), { addSuffix: true })}
                </h6>
                <p className="text-muted mb-0">Created</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="card-title mb-0">Service Actions</h5>
                <div className="btn-group">
                  <button
                    className="btn btn-success"
                    onClick={handleScaleClick}
                    disabled={service.mode !== 'replicated'}
                  >
                    <i className="mdi mdi-resize me-1"></i>
                    Scale
                  </button>
                  <button
                    className="btn btn-warning"
                    onClick={() => {/* TODO: Implement update */}}
                  >
                    <i className="mdi mdi-pencil me-1"></i>
                    Update
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => setShowRemoveModal(true)}
                  >
                    <i className="mdi mdi-delete me-1"></i>
                    Remove
                  </button>
                </div>
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
                    className={`nav-link ${activeTab === 'overview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('overview')}
                    style={{ cursor: 'pointer' }}
                  >
                    <i className="mdi mdi-information me-1"></i>
                    Overview
                  </a>
                </li>
                <li className="nav-item">
                  <a
                    className={`nav-link ${activeTab === 'tasks' ? 'active' : ''}`}
                    onClick={() => setActiveTab('tasks')}
                    style={{ cursor: 'pointer' }}
                  >
                    <i className="mdi mdi-format-list-bulleted me-1"></i>
                    Tasks ({tasks.length})
                  </a>
                </li>
                <li className="nav-item">
                  <a
                    className={`nav-link ${activeTab === 'logs' ? 'active' : ''}`}
                    onClick={() => setActiveTab('logs')}
                    style={{ cursor: 'pointer' }}
                  >
                    <i className="mdi mdi-file-document-outline me-1"></i>
                    Logs
                  </a>
                </li>
              </ul>

              <div className="tab-content">
                {/* Overview Tab */}
                {activeTab === 'overview' && (
                  <div className="tab-pane show active">
                    <div className="row mt-3">
                      <div className="col-md-6">
                        <h6>Basic Information</h6>
                        <table className="table table-sm">
                          <tbody>
                            <tr>
                              <td><strong>Service ID:</strong></td>
                              <td><code>{service.ID}</code></td>
                            </tr>
                            <tr>
                              <td><strong>Name:</strong></td>
                              <td>{service.name}</td>
                            </tr>
                            <tr>
                              <td><strong>Image:</strong></td>
                              <td>{service.image}</td>
                            </tr>
                            <tr>
                              <td><strong>Mode:</strong></td>
                              <td>
                                <span className={`badge ${service.mode === 'replicated' ? 'bg-primary' : 'bg-info'}`}>
                                  {service.mode}
                                </span>
                              </td>
                            </tr>
                            {service.mode === 'replicated' && (
                              <tr>
                                <td><strong>Replicas:</strong></td>
                                <td>{service.replicas}</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                      <div className="col-md-6">
                        <h6>Network & Ports</h6>
                        {service.Endpoint?.Ports?.length > 0 ? (
                          <table className="table table-sm">
                            <thead>
                              <tr>
                                <th>Published</th>
                                <th>Target</th>
                                <th>Protocol</th>
                                <th>Mode</th>
                              </tr>
                            </thead>
                            <tbody>
                              {service.Endpoint.Ports.map((port: any, index: number) => (
                                <tr key={index}>
                                  <td>{port.PublishedPort || '-'}</td>
                                  <td>{port.TargetPort}</td>
                                  <td>{port.Protocol}</td>
                                  <td>{port.PublishMode}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p className="text-muted">No published ports</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Tasks Tab */}
                {activeTab === 'tasks' && (
                  <div className="tab-pane show active">
                    <h6 className="mt-3 mb-3">Service Tasks</h6>
                    <div className="table-responsive">
                      <table className="table table-hover mb-0">
                        <thead>
                          <tr>
                            <th>Task ID</th>
                            <th>Node</th>
                            <th>State</th>
                            <th>Desired State</th>
                            <th>Container</th>
                            <th>Created</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tasks.map((task) => (
                            <tr key={task.ID}>
                              <td><code>{task.ID.substring(0, 12)}</code></td>
                              <td>{task.NodeID?.substring(0, 12) || '-'}</td>
                              <td>
                                <span className={`badge ${
                                  task.Status.State === 'running' ? 'bg-success' :
                                  task.Status.State === 'pending' ? 'bg-warning' :
                                  task.Status.State === 'failed' ? 'bg-danger' :
                                  'bg-secondary'
                                }`}>
                                  {task.Status.State}
                                </span>
                              </td>
                              <td>{task.DesiredState}</td>
                              <td>
                                {task.Status.ContainerStatus?.ContainerID ? (
                                  <code>{task.Status.ContainerStatus.ContainerID.substring(0, 12)}</code>
                                ) : '-'}
                              </td>
                              <td>{formatDistanceToNow(new Date(task.CreatedAt), { addSuffix: true })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Logs Tab */}
                {activeTab === 'logs' && (
                  <div className="tab-pane show active" style={{ height: '600px' }}>
                    <div className="mt-3 h-100">
                      <ServiceLogViewer
                        hostId={hostId!}
                        serviceId={serviceId!}
                        serviceName={service.name}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Scale Modal */}
      {showScaleModal && (
        <div className="modal fade show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
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
                <div className="mb-3">
                  <label className="form-label">Number of Replicas</label>
                  <input
                    type="number"
                    className="form-control"
                    value={replicas}
                    onChange={(e) => setReplicas(Number(e.target.value))}
                    min="0"
                    max="100"
                  />
                </div>
                <div className="alert alert-info">
                  <small>
                    Current: {service.replicas} replicas<br />
                    New: {replicas} replicas
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
                >
                  Scale Service
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Remove Modal */}
      {showRemoveModal && (
        <div className="modal fade show" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
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
                  <strong>Warning!</strong> This action cannot be undone.
                </div>
                <p>Are you sure you want to remove the service <strong>{service.name}</strong>?</p>
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
                >
                  Remove Service
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}