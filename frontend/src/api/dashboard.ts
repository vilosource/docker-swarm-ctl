import { api } from './client'

export interface HostStats {
  containers: number
  containers_running: number
  containers_stopped: number
  containers_paused: number
  images: number
  docker_version?: string
  os_type?: string
  architecture?: string
  memory_total?: number
  cpu_count?: number
}

export interface HostSummary {
  id: string
  name: string
  display_name?: string
  status: 'pending' | 'healthy' | 'unhealthy' | 'unreachable'
  last_health_check?: string
  is_default: boolean
  stats: HostStats
}

export interface HostOverview {
  total: number
  healthy: number
  unhealthy: number
  unreachable: number
  pending: number
}

export interface ResourceStats {
  containers: {
    total: number
    running: number
    stopped: number
    paused: number
  }
  images: {
    total: number
    size: number
  }
  volumes: {
    total: number
    size: number
  }
  networks: {
    total: number
  }
}

export interface DashboardData {
  hosts: HostOverview
  resources: ResourceStats
  host_details: HostSummary[]
  generated_at: string
}

export const dashboardApi = {
  async getDashboard(activeOnly: boolean = true) {
    const response = await api.get<DashboardData>('/dashboard', {
      params: { active_only: activeOnly }
    })
    return response.data
  },

  async refreshHostStats(hostId: string) {
    const response = await api.get(`/dashboard/refresh/${hostId}`)
    return response.data
  }
}