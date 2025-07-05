import { create } from 'zustand'
import { DockerHost, HostStatus } from '@/types'
import { hostsApi } from '@/api/hosts'
import { api } from '@/api/client'

interface HostState {
  hosts: DockerHost[]
  currentHostId: string | null
  loading: boolean
  error: string | null
  
  // Actions
  fetchHosts: () => Promise<void>
  selectHost: (hostId: string | null) => void
  setHosts: (hosts: DockerHost[]) => void
  updateHostStatus: (hostId: string, status: HostStatus) => void
  addHost: (host: DockerHost) => void
  removeHost: (hostId: string) => void
  updateHost: (hostId: string, updates: Partial<DockerHost>) => void
  clearError: () => void
}

export const useHostStore = create<HostState>((set, get) => ({
  hosts: [],
  currentHostId: null,
  loading: false,
  error: null,
  
  fetchHosts: async () => {
    set({ loading: true, error: null })
    try {
      const response = await hostsApi.list({ active_only: true })
      const { hosts } = get()
      
      // Find default host or first available
      const defaultHost = response.items.find(h => h.is_default) || response.items[0]
      const currentHostId = get().currentHostId || defaultHost?.id || null
      
      set({ 
        hosts: response.items, 
        currentHostId,
        loading: false 
      })
      
      // If we have a selected host, update API client
      if (currentHostId) {
        api.defaults.headers.common['X-Docker-Host-ID'] = currentHostId
      }
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch hosts',
        loading: false 
      })
    }
  },
  
  selectHost: (hostId: string | null) => {
    set({ currentHostId: hostId })
    
    // Update API client default header
    if (hostId) {
      api.defaults.headers.common['X-Docker-Host-ID'] = hostId
    } else {
      delete api.defaults.headers.common['X-Docker-Host-ID']
    }
    
    // Store in localStorage for persistence
    if (hostId) {
      localStorage.setItem('selectedHostId', hostId)
    } else {
      localStorage.removeItem('selectedHostId')
    }
  },
  
  setHosts: (hosts: DockerHost[]) => {
    set({ hosts })
  },
  
  updateHostStatus: (hostId: string, status: HostStatus) => {
    set(state => ({
      hosts: state.hosts.map(host => 
        host.id === hostId ? { ...host, status } : host
      )
    }))
  },
  
  addHost: (host: DockerHost) => {
    set(state => ({
      hosts: [...state.hosts, host]
    }))
  },
  
  removeHost: (hostId: string) => {
    set(state => ({
      hosts: state.hosts.filter(h => h.id !== hostId),
      currentHostId: state.currentHostId === hostId ? null : state.currentHostId
    }))
  },
  
  updateHost: (hostId: string, updates: Partial<DockerHost>) => {
    set(state => ({
      hosts: state.hosts.map(host => 
        host.id === hostId ? { ...host, ...updates } : host
      )
    }))
  },
  
  clearError: () => {
    set({ error: null })
  }
}))

// Initialize host selection from localStorage
if (typeof window !== 'undefined') {
  const savedHostId = localStorage.getItem('selectedHostId')
  if (savedHostId) {
    useHostStore.getState().selectHost(savedHostId)
  }
}