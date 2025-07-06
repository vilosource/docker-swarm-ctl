import { api } from './client'
import { Container, ContainerStats } from '@/types'

export interface ContainerCreateRequest {
  image: string
  name?: string
  command?: string[]
  environment?: Record<string, string>
  ports?: Record<string, number>
  volumes?: string[]
  labels?: Record<string, string>
  restart_policy?: 'no' | 'always' | 'on-failure' | 'unless-stopped'
}

export interface ContainerInspect {
  id: string
  name: string
  image: string
  config: any
  environment: string[]
  mounts: any[]
  network_settings: any
  state: any
  host_config: any
}

export const containersApi = {
  list: (all = false, hostId?: string) => 
    api.get<Container[]>('/containers', { params: { all, host_id: hostId } }),
  
  get: (id: string, hostId?: string) => 
    api.get<Container>(`/containers/${id}`, { params: { host_id: hostId } }),
  
  create: (data: ContainerCreateRequest, hostId?: string) => 
    api.post<Container>('/containers', data, { params: { host_id: hostId } }),
  
  start: (id: string, hostId?: string) => 
    api.post(`/containers/${id}/start`, null, { params: { host_id: hostId } }),
  
  stop: (id: string, timeout = 10, hostId?: string) => 
    api.post(`/containers/${id}/stop`, null, { params: { timeout, host_id: hostId } }),
  
  restart: (id: string, timeout = 10, hostId?: string) => 
    api.post(`/containers/${id}/restart`, null, { params: { timeout, host_id: hostId } }),
  
  remove: (id: string, force = false, volumes = false, hostId?: string) => 
    api.delete(`/containers/${id}`, { params: { force, volumes, host_id: hostId } }),
  
  logs: (id: string, lines = 100, timestamps = false, hostId?: string) => 
    api.get<{ container_id: string; logs: string }>(`/containers/${id}/logs`, { 
      params: { lines, timestamps, host_id: hostId } 
    }),
  
  stats: (id: string, hostId?: string) => 
    api.get<ContainerStats>(`/containers/${id}/stats`, { params: { host_id: hostId } }),
  
  inspect: (id: string, hostId?: string) => 
    api.get<ContainerInspect>(`/containers/${id}/inspect`, { params: { host_id: hostId } }),
}