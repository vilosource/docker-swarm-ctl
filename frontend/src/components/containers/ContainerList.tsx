import { Container } from '@/types'
import { format } from 'date-fns'

interface ContainerListProps {
  containers: Container[]
  onStart: (container: Container) => void
  onStop: (container: Container) => void
  onRemove: (container: Container) => void
  canManage: boolean
}

export default function ContainerList({
  containers,
  onStart,
  onStop,
  onRemove,
  canManage,
}: ContainerListProps) {
  const getStatusBadge = (status: string, state: string) => {
    const statusLower = status.toLowerCase()
    const stateLower = state.toLowerCase()
    
    if (stateLower === 'running') {
      return <span className="badge bg-success">Running</span>
    } else if (stateLower === 'exited') {
      return <span className="badge bg-danger">Exited</span>
    } else if (stateLower === 'paused') {
      return <span className="badge bg-warning">Paused</span>
    } else {
      return <span className="badge bg-secondary">{status}</span>
    }
  }
  
  if (containers.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-muted mb-0">No containers found</p>
      </div>
    )
  }
  
  return (
    <div className="table-responsive">
      <table className="table table-hover table-centered mb-0">
        <thead>
          <tr>
            <th>Name</th>
            <th>Image</th>
            <th>Status</th>
            <th>Created</th>
            <th>Ports</th>
            {canManage && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {containers.map((container) => (
            <tr key={container.id}>
              <td>
                <h5 className="font-size-14 mb-1">
                  <a href="#" className="text-dark">{container.name}</a>
                </h5>
                <p className="text-muted mb-0 font-size-12">ID: {container.id}</p>
              </td>
              <td>
                <span className="text-muted font-size-13">{container.image}</span>
              </td>
              <td>
                {getStatusBadge(container.status, container.state)}
              </td>
              <td>
                <span className="text-muted font-size-13">
                  {format(new Date(container.created), 'MMM dd, yyyy')}
                </span>
              </td>
              <td>
                {container.ports && Object.keys(container.ports).length > 0 ? (
                  <div className="font-size-12">
                    {Object.entries(container.ports).map(([containerPort, hostPorts]) => {
                      if (!hostPorts || hostPorts.length === 0) return null
                      return (
                        <div key={containerPort}>
                          {hostPorts.map((hostPort: any, index: number) => (
                            <span key={index} className="badge bg-soft-info text-info me-1">
                              {hostPort.HostPort}→{containerPort}
                            </span>
                          ))}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <span className="text-muted">-</span>
                )}
              </td>
              {canManage && (
                <td>
                  <div className="btn-group btn-group-sm" role="group">
                    {container.state === 'running' ? (
                      <button
                        onClick={() => onStop(container)}
                        className="btn btn-light"
                        data-bs-toggle="tooltip"
                        title="Stop Container"
                      >
                        <i className="mdi mdi-stop"></i>
                      </button>
                    ) : (
                      <button
                        onClick={() => onStart(container)}
                        className="btn btn-light"
                        data-bs-toggle="tooltip"
                        title="Start Container"
                      >
                        <i className="mdi mdi-play"></i>
                      </button>
                    )}
                    <button
                      onClick={() => onRemove(container)}
                      className="btn btn-light text-danger"
                      data-bs-toggle="tooltip"
                      title="Remove Container"
                    >
                      <i className="mdi mdi-delete"></i>
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}