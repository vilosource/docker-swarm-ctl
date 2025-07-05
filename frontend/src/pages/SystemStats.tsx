import PageTitle from '@/components/common/PageTitle'
import { useQuery } from '@tanstack/react-query'
import { systemApi } from '@/api/system'

export default function SystemStats() {
  const { data: systemInfo } = useQuery({
    queryKey: ['system', 'info'],
    queryFn: systemApi.getInfo
  })

  return (
    <>
      <PageTitle 
        title="System Stats"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'System Stats' }
        ]}
      />

      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <h4 className="header-title mb-3">Docker Host System Information</h4>
              <p className="text-muted mb-4">
                System-wide Docker daemon information and resource usage
              </p>
              
              {systemInfo && (
                <div className="row">
                  <div className="col-md-6">
                    <h5>System Overview</h5>
                    <table className="table table-sm">
                      <tbody>
                        <tr>
                          <td>Total Memory:</td>
                          <td>{(systemInfo.mem_total / 1024 / 1024 / 1024).toFixed(2)} GB</td>
                        </tr>
                        <tr>
                          <td>CPUs:</td>
                          <td>{systemInfo.ncpu}</td>
                        </tr>
                        <tr>
                          <td>Operating System:</td>
                          <td>{systemInfo.operating_system}</td>
                        </tr>
                        <tr>
                          <td>Kernel Version:</td>
                          <td>{systemInfo.kernel_version}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="col-md-6">
                    <h5>Docker Info</h5>
                    <table className="table table-sm">
                      <tbody>
                        <tr>
                          <td>Containers:</td>
                          <td>{systemInfo.containers} ({systemInfo.containers_running} running)</td>
                        </tr>
                        <tr>
                          <td>Images:</td>
                          <td>{systemInfo.images}</td>
                        </tr>
                        <tr>
                          <td>Docker Version:</td>
                          <td>{systemInfo.server_version}</td>
                        </tr>
                        <tr>
                          <td>Storage Driver:</td>
                          <td>{systemInfo.driver}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              
              <div className="alert alert-info mt-4">
                <i className="mdi mdi-information me-2"></i>
                <strong>Note:</strong> For container-specific resource usage, visit the individual container's details page.
                Real-time stats monitoring is available for each running container.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}