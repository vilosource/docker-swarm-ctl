export interface VolumeCreate {
  name?: string
  driver?: string
  driver_opts?: Record<string, string>
  labels?: Record<string, string>
}

export interface Volume {
  name: string
  driver: string
  mountpoint: string
  created_at?: string
  status?: Record<string, any>
  labels: Record<string, string>
  scope: string
  options?: Record<string, string>
  host_id?: string
  host_name?: string
}

export interface VolumeInspect extends Volume {
  usage_data?: {
    Size: number
    RefCount: number
  }
}

export interface VolumePruneResponse {
  volumes_deleted: string[]
  space_reclaimed: number
}