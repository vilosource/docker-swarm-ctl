import { Container } from '@/types'
import { format } from 'date-fns'
import { Link } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import { initResponsiveTable } from '@/utils/responsiveTable'

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
  const tableRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    // Initialize responsive table when component mounts or containers change
    if (tableRef.current) {
      initResponsiveTable(tableRef.current)
    }
  }, [containers])
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
    <div className="responsive-table-plugin" ref={tableRef}>
      <div className="table-rep-plugin">
        <div className="table-responsive" data-pattern="priority-columns">
          <table className="table table-striped table-hover mb-0">
            <thead>
              <tr>
                <th data-priority="1">Name</th>
                <th data-priority="2">ID</th>
                <th data-priority="3">Image</th>
                <th data-priority="1">Status</th>
                <th data-priority="4">Compose</th>
                <th data-priority="3">Created</th>
                <th data-priority="5">Ports</th>
                {canManage && <th data-priority="1">Actions</th>}
              </tr>
            </thead>
        <tbody>
          {containers.map((container) => (
            <tr key={container.id}>
              <td>
                <h5 className="font-14 mb-0">
                  <Link to={`/containers/${container.id}`} className="text-dark">{container.name}</Link>
                </h5>
              </td>
              <td>
                <code className="font-12">{container.id.substring(0, 12)}</code>
              </td>
              <td>
                <span className="text-muted font-size-13">{container.image}</span>
              </td>
              <td>
                {getStatusBadge(container.status, container.state)}
              </td>
              <td>
                {container.labels?.['com.docker.compose.project'] ? (
                  <div>
                    <span className="font-12">{container.labels['com.docker.compose.project']}</span>
                    <br />
                    <small className="text-muted">{container.labels['com.docker.compose.service']}</small>
                  </div>
                ) : (
                  <span className="text-muted">-</span>
                )}
              </td>
              <td>
                <span className="text-muted font-size-13">
                  {format(new Date(container.created), 'MMM dd, yyyy')}
                </span>
              </td>
              <td>
                {container.ports && Object.keys(container.ports).length > 0 ? (
                  <div>
                    {Object.entries(container.ports).map(([containerPort, hostPorts]) => {
                      if (!hostPorts || hostPorts.length === 0) return null
                      return hostPorts.map((hostPort: any, index: number) => (
                        <span key={`${containerPort}-${index}`} className="badge bg-soft-info text-info me-1 mb-1">
                          {hostPort.HostPort}→{containerPort}
                        </span>
                      ))
                    })}
                  </div>
                ) : (
                  <span className="text-muted">-</span>
                )}
              </td>
              {canManage && (
                <td>
                  <div className="btn-group btn-group-sm" role="group">
                    <Link
                      to={`/containers/${container.id}`}
                      className="btn btn-light"
                      data-bs-toggle="tooltip"
                      title="View Details & Logs"
                    >
                      <i className="mdi mdi-eye"></i>
                    </Link>
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
      </div>
    </div>
  )
}