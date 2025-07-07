import { api } from './client'
import { Volume, VolumeCreate, VolumeInspect, VolumePruneResponse } from '@/types/volume'

export const volumesApi = {
  // List volumes
  async list(params?: { filters?: any; host_id?: string }) {
    const response = await api.get<Volume[]>('/volumes', {
      params: {
        filters: params?.filters ? JSON.stringify(params.filters) : undefined,
        host_id: params?.host_id
      }
    })
    return response.data
  },

  // Create volume
  async create(data: VolumeCreate, hostId?: string) {
    const response = await api.post<Volume>('/volumes', data, {
      params: { host_id: hostId }
    })
    return response.data
  },

  // Get volume details
  async get(volumeName: string, hostId?: string) {
    const response = await api.get<VolumeInspect>(`/volumes/${volumeName}`, {
      params: { host_id: hostId }
    })
    return response.data
  },

  // Remove volume
  async remove(volumeName: string, force?: boolean, hostId?: string) {
    await api.delete(`/volumes/${volumeName}`, {
      params: {
        force,
        host_id: hostId
      }
    })
  },

  // Prune unused volumes
  async prune(filters?: any, hostId?: string) {
    const response = await api.post<VolumePruneResponse>('/volumes/prune', null, {
      params: {
        filters: filters ? JSON.stringify(filters) : undefined,
        host_id: hostId
      }
    })
    return response.data
  }
}