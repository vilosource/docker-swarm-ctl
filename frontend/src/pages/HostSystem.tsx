import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { systemApi } from '@/api/system'
import { hostsApi } from '@/api/hosts'
import PageTitle from '@/components/common/PageTitle'
import { formatBytes } from '@/utils/format'

export default function HostSystem() {
  const { hostId } = useParams<{ hostId: string }>()
  
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
        title={`System - ${host?.data.name || 'Loading...'}`}
        breadcrumb={[
          { title: 'Hosts', href: '/hosts' },
          { title: host?.data.name || 'Loading...', href: `/hosts/${hostId}` },
          { title: 'System' }
        ]}
      />
      
      <div className="row">
        {/* System Information Card */}
        <div className="col-xl-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">System Information</h5>
              <div className="table-responsive">
                <table className="table table-sm">
                  <tbody>
                    <tr>
                      <td className="fw-medium">Operating System</td>
                      <td>{systemInfo?.operating_system}</td>
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
                      <td>{systemInfo?.ncpu}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Total Memory</td>
                      <td>{systemInfo?.mem_total ? formatBytes(systemInfo.mem_total) : '-'}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Docker Root Dir</td>
                      <td>{systemInfo?.docker_root_dir}</td>
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
        <div className="col-xl-6">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">Docker Version</h5>
              <div className="table-responsive">
                <table className="table table-sm">
                  <tbody>
                    <tr>
                      <td className="fw-medium">Docker Version</td>
                      <td>{systemVersion?.version}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">API Version</td>
                      <td>{systemVersion?.api_version}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Min API Version</td>
                      <td>{systemVersion?.min_api_version}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Go Version</td>
                      <td>{systemVersion?.go_version}</td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Git Commit</td>
                      <td><code>{systemVersion?.git_commit}</code></td>
                    </tr>
                    <tr>
                      <td className="fw-medium">Build Time</td>
                      <td>{systemVersion?.build_time}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        
        {/* Container Stats Card */}
        <div className="col-xl-4">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">Containers</h5>
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
        
        {/* Image Stats Card */}
        <div className="col-xl-4">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">Images</h5>
              <div className="d-flex justify-content-between mb-2">
                <span>Total Images</span>
                <span className="fw-bold">{systemInfo?.images || 0}</span>
              </div>
              {diskUsage && (
                <>
                  <div className="d-flex justify-content-between mb-2">
                    <span>Total Size</span>
                    <span className="fw-bold">
                      {formatBytes(diskUsage.images.reduce((acc, img) => acc + img.size, 0))}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span>Layers Size</span>
                    <span className="fw-bold">{formatBytes(diskUsage.layers_size)}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
        
        {/* Disk Usage Card */}
        <div className="col-xl-4">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title mb-3">Disk Usage</h5>
              {diskUsage && (
                <>
                  <div className="d-flex justify-content-between mb-2">
                    <span>Volumes</span>
                    <span className="fw-bold">
                      {diskUsage.volumes.length} ({formatBytes(
                        diskUsage.volumes.reduce((acc, vol) => acc + vol.size, 0)
                      )})
                    </span>
                  </div>
                  <div className="d-flex justify-content-between mb-2">
                    <span>Build Cache</span>
                    <span className="fw-bold">-</span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-info">Total</span>
                    <span className="fw-bold text-info">
                      {formatBytes(
                        diskUsage.layers_size +
                        diskUsage.images.reduce((acc, img) => acc + img.size, 0) +
                        diskUsage.volumes.reduce((acc, vol) => acc + vol.size, 0) +
                        diskUsage.containers.reduce((acc, cnt) => acc + cnt.size_rw, 0)
                      )}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}