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