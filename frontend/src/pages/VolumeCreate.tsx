import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import PageTitle from '@/components/common/PageTitle'
import { volumesApi } from '@/api/volumes'
import { hostsApi } from '@/api/hosts'

interface VolumeFormData {
  name: string
  driver: string
  driver_opts: Record<string, string>
  labels: Record<string, string>
}

export default function VolumeCreate() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const hostId = searchParams.get('host_id')
  
  const [formData, setFormData] = useState<VolumeFormData>({
    name: '',
    driver: 'local',
    driver_opts: {},
    labels: {}
  })
  
  const [driverOpt, setDriverOpt] = useState({ key: '', value: '' })
  const [label, setLabel] = useState({ key: '', value: '' })
  
  // Fetch hosts for selection
  const { data: hostsData } = useQuery({
    queryKey: ['hosts', 'active'],
    queryFn: () => hostsApi.list({ active_only: true })
  })
  
  const hosts = hostsData?.items || []
  
  const createMutation = useMutation({
    mutationFn: (data: VolumeFormData) => 
      volumesApi.create(data, hostId || undefined),
    onSuccess: () => {
      navigate(hostId ? `/hosts/${hostId}/volumes` : '/volumes')
    }
  })
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await createMutation.mutateAsync(formData)
  }
  
  const addDriverOpt = () => {
    if (driverOpt.key && driverOpt.value) {
      setFormData({
        ...formData,
        driver_opts: {
          ...formData.driver_opts,
          [driverOpt.key]: driverOpt.value
        }
      })
      setDriverOpt({ key: '', value: '' })
    }
  }
  
  const removeDriverOpt = (key: string) => {
    const opts = { ...formData.driver_opts }
    delete opts[key]
    setFormData({ ...formData, driver_opts: opts })
  }
  
  const addLabel = () => {
    if (label.key && label.value) {
      setFormData({
        ...formData,
        labels: {
          ...formData.labels,
          [label.key]: label.value
        }
      })
      setLabel({ key: '', value: '' })
    }
  }
  
  const removeLabel = (key: string) => {
    const labels = { ...formData.labels }
    delete labels[key]
    setFormData({ ...formData, labels })
  }
  
  return (
    <>
      <PageTitle 
        title="Create Volume"
        breadcrumb={[
          { title: 'Resources', href: '#' },
          { title: 'Volumes', href: '/volumes' },
          { title: 'Create' }
        ]}
      />
      
      <div className="card">
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="row g-3">
              {/* Name */}
              <div className="col-md-6">
                <label className="form-label">Name</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="my-volume (leave empty for auto-generated)"
                />
                <small className="text-muted">
                  Optional. Docker will generate a name if not provided.
                </small>
              </div>
              
              {/* Driver */}
              <div className="col-md-6">
                <label className="form-label">Driver</label>
                <select
                  className="form-select"
                  value={formData.driver}
                  onChange={(e) => setFormData({ ...formData, driver: e.target.value })}
                >
                  <option value="local">Local</option>
                  <option value="nfs">NFS</option>
                  <option value="tmpfs">Tmpfs</option>
                  <option value="btrfs">Btrfs</option>
                  <option value="zfs">ZFS</option>
                </select>
              </div>
              
              {/* Host Selection (if not pre-selected) */}
              {!hostId && hosts.length > 0 && (
                <div className="col-12">
                  <label className="form-label">Target Host</label>
                  <select 
                    className="form-select"
                    onChange={(e) => {
                      if (e.target.value) {
                        navigate(`/volumes/create?host_id=${e.target.value}`)
                      }
                    }}
                  >
                    <option value="">Default Host</option>
                    {hosts.map(host => (
                      <option key={host.id} value={host.id}>
                        {host.display_name || host.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              {/* Driver Options */}
              <div className="col-12">
                <label className="form-label">Driver Options</label>
                <div className="card bg-light">
                  <div className="card-body">
                    {Object.entries(formData.driver_opts).length > 0 && (
                      <div className="mb-3">
                        {Object.entries(formData.driver_opts).map(([key, value]) => (
                          <div key={key} className="d-flex align-items-center mb-2">
                            <code className="me-2">{key}={value}</code>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger ms-auto"
                              onClick={() => removeDriverOpt(key)}
                            >
                              <i className="mdi mdi-close"></i>
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <div className="row g-2">
                      <div className="col">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Key"
                          value={driverOpt.key}
                          onChange={(e) => setDriverOpt({ ...driverOpt, key: e.target.value })}
                        />
                      </div>
                      <div className="col">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Value"
                          value={driverOpt.value}
                          onChange={(e) => setDriverOpt({ ...driverOpt, value: e.target.value })}
                        />
                      </div>
                      <div className="col-auto">
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={addDriverOpt}
                          disabled={!driverOpt.key || !driverOpt.value}
                        >
                          Add
                        </button>
                      </div>
                    </div>
                    
                    <small className="text-muted d-block mt-2">
                      Driver-specific options. For example: type=nfs, device=:/path/to/dir
                    </small>
                  </div>
                </div>
              </div>
              
              {/* Labels */}
              <div className="col-12">
                <label className="form-label">Labels</label>
                <div className="card bg-light">
                  <div className="card-body">
                    {Object.entries(formData.labels).length > 0 && (
                      <div className="mb-3">
                        {Object.entries(formData.labels).map(([key, value]) => (
                          <div key={key} className="d-flex align-items-center mb-2">
                            <span className="badge bg-secondary me-2">{key}={value}</span>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger ms-auto"
                              onClick={() => removeLabel(key)}
                            >
                              <i className="mdi mdi-close"></i>
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <div className="row g-2">
                      <div className="col">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Key"
                          value={label.key}
                          onChange={(e) => setLabel({ ...label, key: e.target.value })}
                        />
                      </div>
                      <div className="col">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          placeholder="Value"
                          value={label.value}
                          onChange={(e) => setLabel({ ...label, value: e.target.value })}
                        />
                      </div>
                      <div className="col-auto">
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={addLabel}
                          disabled={!label.key || !label.value}
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Error Message */}
            {createMutation.isError && (
              <div className="alert alert-danger mt-3">
                <i className="mdi mdi-alert-circle me-2"></i>
                {(createMutation.error as any)?.response?.data?.error?.message || 'Failed to create volume'}
              </div>
            )}
            
            {/* Form Actions */}
            <div className="mt-4">
              <button
                type="submit"
                className="btn btn-primary me-2"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Creating...
                  </>
                ) : (
                  <>
                    <i className="mdi mdi-plus-circle me-1"></i>
                    Create Volume
                  </>
                )}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate(-1)}
                disabled={createMutation.isPending}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}