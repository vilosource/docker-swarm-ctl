import { api } from './client'
import { 
  Network, 
  NetworkCreate, 
  NetworkInspect, 
  NetworkConnect, 
  NetworkDisconnect, 
  NetworkPruneResponse 
} from '@/types/network'

export const networksApi = {
  // List networks
  async list(params?: { filters?: any; host_id?: string }) {
    const response = await api.get<Network[]>('/networks', {
      params: {
        filters: params?.filters ? JSON.stringify(params.filters) : undefined,
        host_id: params?.host_id
      }
    })
    return response.data
  },

  // Create network
  async create(data: NetworkCreate, hostId?: string) {
    const response = await api.post<Network>('/networks', data, {
      params: { host_id: hostId }
    })
    return response.data
  },

  // Get network details
  async get(networkId: string, hostId?: string) {
    const response = await api.get<NetworkInspect>(`/networks/${networkId}`, {
      params: { host_id: hostId }
    })
    return response.data
  },

  // Remove network
  async delete(networkId: string, hostId?: string) {
    await api.delete(`/networks/${networkId}`, {
      params: { host_id: hostId }
    })
  },

  // Connect container to network
  async connect(networkId: string, data: NetworkConnect, hostId?: string) {
    await api.post(`/networks/${networkId}/connect`, data, {
      params: { host_id: hostId }
    })
  },

  // Disconnect container from network
  async disconnect(networkId: string, data: NetworkDisconnect, hostId?: string) {
    await api.post(`/networks/${networkId}/disconnect`, data, {
      params: { host_id: hostId }
    })
  },

  // Prune unused networks
  async prune(filters?: any, hostId?: string) {
    const response = await api.post<NetworkPruneResponse>('/networks/prune', null, {
      params: {
        filters: filters ? JSON.stringify(filters) : undefined,
        host_id: hostId
      }
    })
    return response.data
  }
}