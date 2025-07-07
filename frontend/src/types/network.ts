export interface NetworkCreate {
  name: string
  driver?: string
  options?: Record<string, string>
  ipam?: {
    Driver?: string
    Config?: Array<{
      Subnet?: string
      Gateway?: string
      IPRange?: string
    }>
    Options?: Record<string, string>
  }
  enable_ipv6?: boolean
  internal?: boolean
  attachable?: boolean
  labels?: Record<string, string>
}

export interface Network {
  id: string
  name: string
  driver: string
  scope: string
  ipam?: any
  internal: boolean
  attachable: boolean
  ingress: boolean
  containers: Record<string, any>
  options?: Record<string, string>
  labels: Record<string, string>
  created?: string
  enable_ipv6: boolean
  host_id?: string
  host_name?: string
}

export interface NetworkInspect extends Network {
  config_from?: any
  config_only: boolean
}

export interface NetworkConnect {
  container: string
  endpoint_config?: {
    IPAMConfig?: {
      IPv4Address?: string
      IPv6Address?: string
    }
    Links?: string[]
    Aliases?: string[]
  }
}

export interface NetworkDisconnect {
  container: string
  force?: boolean
}

export interface NetworkPruneResponse {
  networks_deleted: string[]
}