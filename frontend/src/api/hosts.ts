import { api } from './client'
import { 
  DockerHost, 
  DockerHostCreate, 
  DockerHostUpdate, 
  HostConnectionTest,
  UserHostPermission,
  PaginatedResponse 
} from '@/types'

export const hostsApi = {
  // List hosts
  async list(params?: { page?: number; per_page?: number; active_only?: boolean }) {
    const response = await api.get<PaginatedResponse<DockerHost>>('/hosts', { params })
    return response.data
  },

  // Get single host
  async get(hostId: string) {
    const response = await api.get<DockerHost>(`/hosts/${hostId}`)
    return response.data
  },

  // Create host
  async create(data: DockerHostCreate) {
    const response = await api.post<DockerHost>('/hosts', data)
    return response.data
  },

  // Update host
  async update(hostId: string, data: DockerHostUpdate) {
    const response = await api.put<DockerHost>(`/hosts/${hostId}`, data)
    return response.data
  },

  // Delete host
  async delete(hostId: string) {
    await api.delete(`/hosts/${hostId}`)
  },

  // Test host connection
  async testConnection(hostId: string) {
    const response = await api.post<HostConnectionTest>(`/hosts/${hostId}/test`)
    return response.data
  },

  // Get host permissions
  async getPermissions(hostId: string) {
    const response = await api.get<UserHostPermission[]>(`/hosts/${hostId}/permissions`)
    return response.data
  },

  // Grant permission
  async grantPermission(hostId: string, userId: string, permissionLevel: string) {
    const response = await api.post<UserHostPermission>(`/hosts/${hostId}/permissions`, {
      user_id: userId,
      permission_level: permissionLevel
    })
    return response.data
  },

  // Revoke permission
  async revokePermission(hostId: string, userId: string) {
    await api.delete(`/hosts/${hostId}/permissions/${userId}`)
  }
}