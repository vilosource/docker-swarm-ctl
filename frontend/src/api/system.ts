import { api } from './client'

export interface SystemInfo {
  id: string
  containers: number
  containers_running: number
  containers_paused: number
  containers_stopped: number
  images: number
  driver: string
  driver_status: Array<[string, string]>
  docker_root_dir: string
  system_status: null
  plugins: {
    volume: string[]
    network: string[]
    authorization: null
    log: string[]
  }
  mem_limit: boolean
  swap_limit: boolean
  kernel_memory: boolean
  kernel_memory_tcp: boolean
  cpu_cfs_period: boolean
  cpu_cfs_quota: boolean
  cpu_shares: boolean
  cpu_set: boolean
  pids_limit: boolean
  ipv4_forwarding: boolean
  bridge_nf_iptables: boolean
  bridge_nf_ip6tables: boolean
  debug: boolean
  n_fd: number
  n_goroutines: number
  system_time: string
  logging_driver: string
  cgroup_driver: string
  cgroup_version: string
  n_events_listener: number
  kernel_version: string
  operating_system: string
  os_version: string
  os_type: string
  architecture: string
  index_server_address: string
  registry_config: any
  ncpu: number
  mem_total: number
  generic_resources: null
  http_proxy: string
  https_proxy: string
  no_proxy: string
  name: string
  labels: string[]
  experimental_build: boolean
  server_version: string
  runtimes: any
  default_runtime: string
  swarm: any
  live_restore_enabled: boolean
  isolation: string
  init_binary: string
  containerd_commit: {
    id: string
    expected: string
  }
  runc_commit: {
    id: string
    expected: string
  }
  init_commit: {
    id: string
    expected: string
  }
  security_options: string[]
  warnings: null
}

export interface SystemVersion {
  platform: {
    name: string
  }
  components: Array<{
    name: string
    version: string
    details: any
  }>
  version: string
  api_version: string
  min_api_version: string
  git_commit: string
  go_version: string
  os: string
  arch: string
  kernel_version: string
  build_time: string
}

export interface DiskUsage {
  containers: Array<{
    id: string
    names: string[]
    image: string
    image_id: string
    command: string
    created: number
    ports: any[]
    size_rw: number
    size_root_fs: number
    labels: Record<string, string>
    state: string
    status: string
    host_config: any
    network_settings: any
    mounts: any[]
  }>
  images: Array<{
    containers: number
    created: number
    id: string
    labels: Record<string, string> | null
    parent_id: string
    repo_digests: string[]
    repo_tags: string[]
    shared_size: number
    size: number
  }>
  volumes: Array<{
    driver: string
    labels: Record<string, string> | null
    mountpoint: string
    name: string
    options: Record<string, string> | null
    scope: string
    created_at: string
    size: number
    ref_count: number
  }>
  build_cache: null
  layers_size: number
}

export const systemApi = {
  getInfo: async (hostId?: string) => {
    const response = await api.get<SystemInfo>('/system/info', { params: { host_id: hostId } })
    return response.data
  },

  getVersion: async (hostId?: string) => {
    const response = await api.get<SystemVersion>('/system/version', { params: { host_id: hostId } })
    return response.data
  },

  getDiskUsage: async (hostId?: string) => {
    const response = await api.get<DiskUsage>('/system/df', { params: { host_id: hostId } })
    return response.data
  },

  prune: async (volumes = false, hostId?: string) => {
    const response = await api.post('/system/prune', null, { params: { volumes, host_id: hostId } })
    return response.data
  }
}