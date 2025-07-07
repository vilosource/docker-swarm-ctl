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
  Id: string
  Name: string
  Driver: string
  Scope: string
  IPAM?: any
  Internal: boolean
  Attachable: boolean
  Ingress: boolean
  Containers: Record<string, any>
  Options?: Record<string, string>
  Labels: Record<string, string>
  Created?: string
  EnableIPv6: boolean
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