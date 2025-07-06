export interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: 'admin' | 'operator' | 'viewer'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Container {
  id: string
  name: string
  image: string
  status: string
  state: string
  created: string
  ports: Record<string, any>
  labels: Record<string, string>
  host_id?: string
  host_name?: string
}

export interface ContainerStats {
  cpu_percent: number
  memory_usage: number
  memory_limit: number
  memory_percent: number
  network_rx: number
  network_tx: number
  block_read: number
  block_write: number
  pids: number
}

export interface Image {
  id: string
  tags: string[]
  created: string
  size: number
  labels: Record<string, string>
  host_id?: string
  host_name?: string
}

export interface ErrorResponse {
  error: {
    code: string
    message: string
    details?: Record<string, any>
    field?: string
  }
  status: 'error'
  request_id?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export type HostType = 'standalone' | 'swarm_manager' | 'swarm_worker'
export type ConnectionType = 'unix' | 'tcp' | 'ssh'
export type HostStatus = 'pending' | 'healthy' | 'unhealthy' | 'unreachable'

export interface HostTag {
  id: string
  tag_name: string
  tag_value?: string
}

export interface DockerHost {
  id: string
  name: string
  description?: string
  host_type: HostType
  connection_type: ConnectionType
  host_url: string
  is_active: boolean
  is_default: boolean
  status: HostStatus
  last_health_check?: string
  docker_version?: string
  api_version?: string
  os_type?: string
  architecture?: string
  swarm_id?: string
  cluster_name?: string
  is_leader: boolean
  created_at: string
  updated_at: string
  tags: HostTag[]
}

export interface HostCredential {
  credential_type: string
  credential_value: string
  credential_metadata?: Record<string, any>
}

export interface DockerHostCreate {
  name: string
  description?: string
  host_type: HostType
  connection_type: ConnectionType
  host_url: string
  is_active: boolean
  is_default: boolean
  tags?: Array<{ tag_name: string; tag_value?: string }>
  credentials?: HostCredential[]
}

export interface DockerHostUpdate {
  name?: string
  description?: string
  host_url?: string
  is_active?: boolean
  is_default?: boolean
}

export interface HostConnectionTest {
  success: boolean
  message: string
  docker_version?: string
  api_version?: string
  error?: string
}

export interface UserHostPermission {
  id: string
  user_id: string
  host_id: string
  permission_level: 'viewer' | 'operator' | 'admin'
  granted_by?: string
  granted_at: string
}