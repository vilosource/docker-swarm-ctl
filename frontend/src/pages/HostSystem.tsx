import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { systemApi } from '@/api/system'
import { hostsApi } from '@/api/hosts'
import PageTitle from '@/components/common/PageTitle'
import { formatBytes } from '@/utils/format'
import { useToast } from '@/hooks/useToast'

export default function HostSystem() {
  const { hostId } = useParams<{ hostId: string }>()
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  
  const { data: host } = useQuery({
    queryKey: ['hosts', hostId],
    queryFn: () => hostsApi.get(hostId!),
    enabled: !!hostId,
  })
  
  const { data: systemInfo, isLoading: infoLoading } = useQuery({
    queryKey: ['system', 'info', hostId],
    queryFn: () => systemApi.getInfo(hostId),
    enabled: !!hostId,
  })
  
  const { data: systemVersion } = useQuery({
    queryKey: ['system', 'version', hostId],
    queryFn: () => systemApi.getVersion(hostId),
    enabled: !!hostId,
  })
  
  const { data: diskUsage } = useQuery({
    queryKey: ['system', 'df', hostId],
    queryFn: () => systemApi.getDiskUsage(hostId),
    enabled: !!hostId,
  })
  
  const { data: circuitBreakers } = useQuery({
    queryKey: ['circuit-breakers'],
    queryFn: () => systemApi.getCircuitBreakers(),
    refetchInterval: 5000 // Refresh every 5 seconds
  })
  
  const resetCircuitBreakerMutation = useMutation({
    mutationFn: () => systemApi.resetCircuitBreaker(`docker-host-${hostId}`),
    onSuccess: () => {
      showToast('Circuit breaker reset successfully', 'success')
      queryClient.invalidateQueries({ queryKey: ['circuit-breakers'] })
      queryClient.invalidateQueries({ queryKey: ['hosts'] })
    },
    onError: (error) => {
      showToast('Failed to reset circuit breaker', 'error')
    }
  })
  
  const getCircuitBreakerStatus = () => {
    if (!circuitBreakers || !hostId) return null
    const breakerName = `docker-host-${hostId}`
    return circuitBreakers[breakerName]
  }
  
  const isCircuitBreakerOpen = () => {
    const status = getCircuitBreakerStatus()
    return status?.state === 'OPEN'
  }
  
  if (infoLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }
  
  return (
    <>
      <PageTitle 
        title="System Information"
        breadcrumb={[
          { title: 'Hosts', href: '/hosts' },
          { title: host?.display_name || host?.name || 'Host', href: `/hosts/${hostId}/system` },
          { title: 'System' }
        ]}
      />
      
      {/* Host Details Card */}
      {host && (
        <div className="row mb-3">
          <div className="col-12">
            <div className="card">
              <div className="card-body">
                <div className="row align-items-center">
                  <div className="col-sm-6">
                    <h5 className="mb-0">
                      <i className="mdi mdi-server me-2"></i>
                      {host.display_name || host.name}
                    </h5>
                    <p className="text-muted mb-0">{host.url}</p>
                  </div>
                  <div className="col-sm-6 text-sm-end">
                    <span className={`badge bg-${host.status === 'healthy' ? 'success' : host.status === 'unhealthy' ? 'danger' : 'warning'} p-2`}>
                      <i className={`mdi mdi-circle me-1`}></i>
                      {host.status.toUpperCase()}
                    </span>
                    {isCircuitBreakerOpen() && (
                      <span className="badge bg-warning ms-2 p-2" title="Circuit breaker is open">
                        <i className="mdi mdi-alert"></i> Circuit Open
                      </span>
                    )}
                    {host.is_default && (
                      <span className="badge bg-info ms-2 p-2">DEFAULT</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div className="row">
        {/* System Information Card */}
        <div className="col-xl-6 mb-3">
          <div className="card h-100">
            <div className="card-body">
              <h5 className="card-title mb-3">System Information</h5>
              <div className="table-responsive">
                <table className="table table-sm">
                  <tbody>
                    <tr>
                      <td className="fw-medium">Operating System</td>
                      <td>{systemInfo?.os}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Architecture</td>
                      <td>{systemInfo?.architecture}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Kernel Version</td>
                      <td>{systemInfo?.kernel_version}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">CPUs</td>
                      <td>{systemInfo?.cpu_count}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Total Memory</td>
                      <td>{systemInfo?.memory_total ? formatBytes(systemInfo.memory_total) : '-'}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Storage Driver</td>
                      <td>{systemInfo?.driver}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        
        {/* Docker Version Card */}
        <div className="col-xl-6 mb-3">
          <div className="card h-100">
            <div className="card-body">
              <h5 className="card-title mb-3">Docker Version</h5>
              <div className="table-responsive">
                <table className="table table-sm">
                  <tbody>
                    <tr>
                      <td className="fw-medium">Docker Version</td>
                      <td>{systemInfo?.docker_version || systemVersion?.Version}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">API Version</td>
                      <td>{systemInfo?.api_version || systemVersion?.ApiVersion}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Min API Version</td>
                      <td>{systemVersion?.MinAPIVersion || '-'}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Go Version</td>
                      <td>{systemVersion?.GoVersion || '-'}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Git Commit</td>
                      <td><code>{systemVersion?.GitCommit || '-'}</code></td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Build Time</td>
                      <td>{systemVersion?.BuildTime || '-'}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Stats Row */}
      <div className="row">
        {/* Container Stats Card */}
        <div className="col-xl-4 mb-3">
          <div className="card h-100">
            <div className="card-body d-flex flex-column">
              <h5 className="card-title mb-3">Containers</h5>
              <div className="flex-grow-1">
                <div className="d-flex justify-content-between mb-2">
                  <span>Total</span>
                  <span className="fw-bold">{systemInfo?.containers || 0}</span>
                </div>
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-success">Running</span>
                  <span className="fw-bold text-success">{systemInfo?.containers_running || 0}</span>
                </div>
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-warning">Paused</span>
                  <span className="fw-bold text-warning">{systemInfo?.containers_paused || 0}</span>
                </div>
                <div className="d-flex justify-content-between">
                  <span className="text-danger">Stopped</span>
                  <span className="fw-bold text-danger">{systemInfo?.containers_stopped || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Image Stats Card */}
        <div className="col-xl-4 mb-3">
          <div className="card h-100">
            <div className="card-body d-flex flex-column">
              <h5 className="card-title mb-3">Images</h5>
              <div className="flex-grow-1">
                <div className="d-flex justify-content-between mb-2">
                  <span>Total Images</span>
                  <span className="fw-bold">{systemInfo?.images || 0}</span>
                </div>
                {diskUsage && (
                  <>
                    <div className="d-flex justify-content-between mb-2">
                      <span>Total Size</span>
                      <span className="fw-bold">
                        {formatBytes(diskUsage.images?.size || 0)}
                      </span>
                    </div>
                    <div className="d-flex justify-content-between">
                      <span>Layers Size</span>
                      <span className="fw-bold">{formatBytes(diskUsage.layers_size || 0)}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
        
        {/* Disk Usage Card */}
        <div className="col-xl-4 mb-3">
          <div className="card h-100">
            <div className="card-body d-flex flex-column">
              <h5 className="card-title mb-3">Disk Usage</h5>
              <div className="flex-grow-1">
                {diskUsage ? (
                  <>
                    <div className="d-flex justify-content-between mb-2">
                      <span>Volumes</span>
                      <span className="fw-bold">
                        {diskUsage.volumes?.count || 0} ({formatBytes(diskUsage.volumes?.size || 0)})
                      </span>
                    </div>
                    <div className="d-flex justify-content-between mb-2">
                      <span>Containers</span>
                      <span className="fw-bold">
                        {diskUsage.containers?.count || 0} ({formatBytes(diskUsage.containers?.size || 0)})
                      </span>
                    </div>
                    <div className="d-flex justify-content-between">
                      <span className="text-info">Total</span>
                      <span className="fw-bold text-info">
                        {formatBytes(
                          (diskUsage.layers_size || 0) +
                          (diskUsage.images?.size || 0) +
                          (diskUsage.volumes?.size || 0) +
                          (diskUsage.containers?.size || 0)
                        )}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="text-muted">Loading...</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Quick Actions */}
      <div className="row mt-3">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">Quick Actions</h5>
              <div className="d-flex gap-2 flex-wrap">
                {isCircuitBreakerOpen() && (
                  <button 
                    className="btn btn-danger"
                    onClick={() => resetCircuitBreakerMutation.mutate()}
                    disabled={resetCircuitBreakerMutation.isPending}
                  >
                    <i className="mdi mdi-refresh me-1"></i>
                    Reset Circuit Breaker
                  </button>
                )}
                <button 
                  className="btn btn-warning"
                  onClick={() => {
                    if (confirm('Are you sure you want to prune the system? This will remove all stopped containers, dangling images, and unused networks.')) {
                      // TODO: Implement system prune
                      alert('System prune functionality to be implemented')
                    }
                  }}
                >
                  <i className="mdi mdi-broom me-1"></i>
                  System Prune
                </button>
                <button 
                  className="btn btn-info"
                  onClick={() => window.location.reload()}
                >
                  <i className="mdi mdi-refresh me-1"></i>
                  Refresh Stats
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}