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

export const containersApi = {
  list: (all = false) => 
    api.get<Container[]>('/containers', { params: { all } }),
  
  get: (id: string) => 
    api.get<Container>(`/containers/${id}`),
  
  create: (data: ContainerCreateRequest) => 
    api.post<Container>('/containers', data),
  
  start: (id: string) => 
    api.post(`/containers/${id}/start`),
  
  stop: (id: string, timeout = 10) => 
    api.post(`/containers/${id}/stop`, null, { params: { timeout } }),
  
  restart: (id: string, timeout = 10) => 
    api.post(`/containers/${id}/restart`, null, { params: { timeout } }),
  
  remove: (id: string, force = false, volumes = false) => 
    api.delete(`/containers/${id}`, { params: { force, volumes } }),
  
  logs: (id: string, lines = 100, timestamps = false) => 
    api.get<{ container_id: string; logs: string }>(`/containers/${id}/logs`, { 
      params: { lines, timestamps } 
    }),
  
  stats: (id: string) => 
    api.get<ContainerStats>(`/containers/${id}/stats`),
}