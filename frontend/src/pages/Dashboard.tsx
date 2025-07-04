import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import PageTitle from '@/components/common/PageTitle'

interface SystemInfo {
  docker_version: string
  os: string
  containers: number
  containers_running: number
  containers_stopped: number
  images: number
  memory_total: number
  cpu_count: number
}

export default function Dashboard() {
  const { data: systemInfo, isLoading } = useQuery({
    queryKey: ['system-info'],
    queryFn: async () => {
      const response = await api.get<SystemInfo>('/system/info')
      return response.data
    },
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
  
  const stats = [
    { 
      label: 'Total Containers', 
      value: systemInfo?.containers || 0, 
      icon: 'mdi mdi-docker',
      color: 'primary' 
    },
    { 
      label: 'Running', 
      value: systemInfo?.containers_running || 0, 
      icon: 'mdi mdi-play-circle',
      color: 'success' 
    },
    { 
      label: 'Stopped', 
      value: systemInfo?.containers_stopped || 0, 
      icon: 'mdi mdi-stop-circle',
      color: 'danger' 
    },
    { 
      label: 'Images', 
      value: systemInfo?.images || 0, 
      icon: 'mdi mdi-layers',
      color: 'info' 
    },
  ]
  
  return (
    <>
      <PageTitle 
        title="Dashboard" 
        breadcrumb={[
          { title: 'Dashboard' }
        ]}
      />
      
      {/* Stats Cards */}
      <div className="row">
        {stats.map((stat) => (
          <div key={stat.label} className="col-md-6 col-xl-3">
            <div className="card">
              <div className="card-body">
                <div className="d-flex">
                  <div className="flex-grow-1">
                    <span className="text-muted text-uppercase fs-12 fw-bold">{stat.label}</span>
                    <h3 className="mb-0">{stat.value}</h3>
                  </div>
                  <div className="align-self-center flex-shrink-0">
                    <div className={`font-size-24 text-${stat.color}`}>
                      <i className={stat.icon}></i>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* System Information */}
      {systemInfo && (
        <div className="row">
          <div className="col-12">
            <div className="card">
              <div className="card-header">
                <h4 className="header-title mb-0">System Information</h4>
              </div>
              <div className="card-body">
                <div className="row">
                  <div className="col-md-6">
                    <div className="mb-3">
                      <label className="form-label text-muted">Docker Version</label>
                      <p className="mb-0">{systemInfo.docker_version}</p>
                    </div>
                    <div className="mb-3">
                      <label className="form-label text-muted">Operating System</label>
                      <p className="mb-0">{systemInfo.os}</p>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="mb-3">
                      <label className="form-label text-muted">CPU Count</label>
                      <p className="mb-0">{systemInfo.cpu_count} cores</p>
                    </div>
                    <div className="mb-3">
                      <label className="form-label text-muted">Total Memory</label>
                      <p className="mb-0">
                        {systemInfo.memory_total ? 
                          `${(systemInfo.memory_total / 1024 / 1024 / 1024).toFixed(2)} GB` : 
                          'N/A'
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}