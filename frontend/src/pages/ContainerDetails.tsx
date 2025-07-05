import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { containersApi } from '@/api/containers'
import { ContainerLogs } from '@/components/ContainerLogs'
import { ContainerTerminal } from '@/components/ContainerTerminal'
import ContainerEnvironment from '@/components/ContainerEnvironment'
import PageTitle from '@/components/common/PageTitle'

export default function ContainerDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('logs')

  const { data: container, isLoading, error } = useQuery({
    queryKey: ['container', id],
    queryFn: async () => {
      if (!id) throw new Error('Container ID is required')
      const response = await containersApi.get(id)
      return response.data
    },
    enabled: !!id,
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

  if (error || !container) {
    return (
      <div className="container-fluid">
        <div className="alert alert-danger" role="alert">
          {error ? error.message : 'Container not found'}
        </div>
        <button className="btn btn-secondary" onClick={() => navigate('/containers')}>
          <i className="mdi mdi-arrow-left me-2"></i>Back to Containers
        </button>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    const statusLower = status.toLowerCase()
    if (statusLower.includes('running')) {
      return <span className="badge bg-success">{status}</span>
    } else if (statusLower.includes('exited')) {
      return <span className="badge bg-danger">{status}</span>
    } else if (statusLower.includes('paused')) {
      return <span className="badge bg-warning">{status}</span>
    } else {
      return <span className="badge bg-secondary">{status}</span>
    }
  }

  return (
    <>
      <PageTitle
        title={container.name || container.id.substring(0, 12)}
        breadcrumb={[
          { title: 'Docker', href: '#' },
          { title: 'Containers', href: '/containers' },
          { title: container.name || container.id.substring(0, 12) }
        ]}
      />

      {/* Container Overview */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body p-3">
              <div className="table-responsive">
                <table className="table table-sm mb-0">
                  <thead>
                    <tr>
                      <th className="text-muted">ID</th>
                      <th className="text-muted">Status</th>
                      <th className="text-muted">Image</th>
                      <th className="text-muted">Created</th>
                      <th className="text-muted">Ports</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="font-monospace">{container.id.substring(0, 12)}</td>
                      <td>{getStatusBadge(container.status)}</td>
                      <td>{container.image}</td>
                      <td>{new Date(container.created).toLocaleString()}</td>
                      <td>
                        {container.ports && Object.keys(container.ports).length > 0 ? (
                          <div className="d-flex flex-wrap">
                            {Object.entries(container.ports).map(([containerPort, hostPorts]) => {
                              if (!hostPorts || hostPorts.length === 0) return null
                              return hostPorts.map((hostPort: any, index: number) => (
                                <span key={`${containerPort}-${index}`} className="badge bg-soft-info text-info me-1">
                                  {hostPort.HostPort}→{containerPort}
                                </span>
                              ))
                            })}
                          </div>
                        ) : (
                          <small className="text-muted">No mappings</small>
                        )}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="row mt-3">
        <div className="col-12">
          <div className="card">
            <div className="card-header py-2">
              <ul className="nav nav-tabs card-header-tabs">
                <li className="nav-item">
                  <a 
                    className={`nav-link ${activeTab === 'logs' ? 'active' : ''}`}
                    href="#"
                    onClick={(e) => { e.preventDefault(); setActiveTab('logs') }}
                  >
                    Logs
                  </a>
                </li>
                <li className="nav-item">
                  <a 
                    className={`nav-link ${activeTab === 'terminal' ? 'active' : ''}`}
                    href="#"
                    onClick={(e) => { e.preventDefault(); setActiveTab('terminal') }}
                  >
                    Terminal
                  </a>
                </li>
                <li className="nav-item">
                  <a 
                    className={`nav-link ${activeTab === 'environment' ? 'active' : ''}`}
                    href="#"
                    onClick={(e) => { e.preventDefault(); setActiveTab('environment') }}
                  >
                    Environment
                  </a>
                </li>
              </ul>
            </div>
            <div className="card-body p-0" style={{ height: 'calc(100vh - 320px)', minHeight: '400px' }}>
              {activeTab === 'logs' && <ContainerLogs containerId={container.id} />}
              {activeTab === 'terminal' && (
                <div className="h-100">
                  <ContainerTerminal containerId={container.id} />
                </div>
              )}
              {activeTab === 'environment' && (
                <div className="p-3">
                  <ContainerEnvironment containerId={container.id} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}