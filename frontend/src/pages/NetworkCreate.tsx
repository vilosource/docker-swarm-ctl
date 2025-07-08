import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import PageTitle from '@/components/common/PageTitle'
import { networksApi } from '@/api/networks'
import { hostsApi } from '@/api/hosts'

interface NetworkFormData {
  name: string
  driver: string
  options: Record<string, string>
  ipam?: {
    Driver?: string
    Config?: Array<{
      Subnet?: string
      IPRange?: string
      Gateway?: string
    }>
  }
  enable_ipv6: boolean
  internal: boolean
  attachable: boolean
  labels: Record<string, string>
}

export default function NetworkCreate() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const hostId = searchParams.get('host_id')
  
  const [formData, setFormData] = useState<NetworkFormData>({
    name: '',
    driver: 'bridge',
    options: {},
    enable_ipv6: false,
    internal: false,
    attachable: true,
    labels: {}
  })
  
  const [driverOpt, setDriverOpt] = useState({ key: '', value: '' })
  const [label, setLabel] = useState({ key: '', value: '' })
  const [ipamConfig, setIpamConfig] = useState({
    subnet: '',
    ip_range: '',
    gateway: ''
  })
  
  // Fetch hosts for selection
  const { data: hostsData } = useQuery({
    queryKey: ['hosts', 'active'],
    queryFn: () => hostsApi.list({ active_only: true })
  })
  
  const hosts = hostsData?.items || []
  
  const createMutation = useMutation({
    mutationFn: (data: NetworkFormData) => 
      networksApi.create(data, hostId || undefined),
    onSuccess: () => {
      navigate(hostId ? `/hosts/${hostId}/networks` : '/networks')
    }
  })
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Build IPAM config if subnet is provided
    let ipam = undefined
    if (ipamConfig.subnet) {
      ipam = {
        Driver: 'default',
        Config: [{
          Subnet: ipamConfig.subnet,
          ...(ipamConfig.ip_range && { IPRange: ipamConfig.ip_range }),
          ...(ipamConfig.gateway && { Gateway: ipamConfig.gateway })
        }]
      }
    }
    
    await createMutation.mutateAsync({
      ...formData,
      ...(ipam && { ipam })
    })
  }
  
  const addDriverOpt = () => {
    if (driverOpt.key && driverOpt.value) {
      setFormData({
        ...formData,
        options: {
          ...formData.options,
          [driverOpt.key]: driverOpt.value
        }
      })
      setDriverOpt({ key: '', value: '' })
    }
  }
  
  const removeDriverOpt = (key: string) => {
    const opts = { ...formData.options }
    delete opts[key]
    setFormData({ ...formData, options: opts })
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
        title="Create Network"
        breadcrumb={[
          { title: 'Resources', href: '#' },
          { title: 'Networks', href: '/networks' },
          { title: 'Create' }
        ]}
      />
      
      <div className="card">
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="row g-3">
              {/* Name */}
              <div className="col-md-6">
                <label className="form-label">Name <span className="text-danger">*</span></label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="my-network"
                  required
                />
              </div>
              
              {/* Driver */}
              <div className="col-md-6">
                <label className="form-label">Driver</label>
                <select
                  className="form-select"
                  value={formData.driver}
                  onChange={(e) => setFormData({ ...formData, driver: e.target.value })}
                >
                  <option value="bridge">Bridge</option>
                  <option value="host">Host</option>
                  <option value="overlay">Overlay</option>
                  <option value="macvlan">Macvlan</option>
                  <option value="none">None</option>
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
                        navigate(`/networks/create?host_id=${e.target.value}`)
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
              
              {/* Network Options */}
              <div className="col-12">
                <label className="form-label">Network Options</label>
                <div className="row g-3">
                  <div className="col-md-4">
                    <div className="form-check">
                      <input
                        type="checkbox"
                        className="form-check-input"
                        id="attachable"
                        checked={formData.attachable}
                        onChange={(e) => setFormData({ ...formData, attachable: e.target.checked })}
                      />
                      <label className="form-check-label" htmlFor="attachable">
                        Attachable
                        <small className="text-muted d-block">
                          Allow manual container attachment
                        </small>
                      </label>
                    </div>
                  </div>
                  <div className="col-md-4">
                    <div className="form-check">
                      <input
                        type="checkbox"
                        className="form-check-input"
                        id="internal"
                        checked={formData.internal}
                        onChange={(e) => setFormData({ ...formData, internal: e.target.checked })}
                      />
                      <label className="form-check-label" htmlFor="internal">
                        Internal
                        <small className="text-muted d-block">
                          Restrict external access
                        </small>
                      </label>
                    </div>
                  </div>
                  <div className="col-md-4">
                    <div className="form-check">
                      <input
                        type="checkbox"
                        className="form-check-input"
                        id="ipv6"
                        checked={formData.enable_ipv6}
                        onChange={(e) => setFormData({ ...formData, enable_ipv6: e.target.checked })}
                      />
                      <label className="form-check-label" htmlFor="ipv6">
                        Enable IPv6
                        <small className="text-muted d-block">
                          Enable IPv6 networking
                        </small>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* IPAM Configuration */}
              <div className="col-12">
                <label className="form-label">IPAM Configuration</label>
                <div className="card bg-light">
                  <div className="card-body">
                    <div className="row g-3">
                      <div className="col-md-4">
                        <label className="form-label">Subnet</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="172.20.0.0/16"
                          value={ipamConfig.subnet}
                          onChange={(e) => setIpamConfig({ ...ipamConfig, subnet: e.target.value })}
                        />
                      </div>
                      <div className="col-md-4">
                        <label className="form-label">IP Range</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="172.20.10.0/24"
                          value={ipamConfig.ip_range}
                          onChange={(e) => setIpamConfig({ ...ipamConfig, ip_range: e.target.value })}
                        />
                      </div>
                      <div className="col-md-4">
                        <label className="form-label">Gateway</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="172.20.0.1"
                          value={ipamConfig.gateway}
                          onChange={(e) => setIpamConfig({ ...ipamConfig, gateway: e.target.value })}
                        />
                      </div>
                    </div>
                    <small className="text-muted d-block mt-2">
                      Optional. Leave empty for automatic IP assignment.
                    </small>
                  </div>
                </div>
              </div>
              
              {/* Driver Options */}
              <div className="col-12">
                <label className="form-label">Driver Options</label>
                <div className="card bg-light">
                  <div className="card-body">
                    {Object.entries(formData.options).length > 0 && (
                      <div className="mb-3">
                        {Object.entries(formData.options).map(([key, value]) => (
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
                      Driver-specific options. For example: com.docker.network.bridge.name=docker1
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
                {(createMutation.error as any)?.response?.data?.error?.message || 'Failed to create network'}
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
                    Create Network
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