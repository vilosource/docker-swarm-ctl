import { api } from './client'
import { Image } from '@/types'

export interface ImagePullRequest {
  repository: string
  tag?: string
  auth_config?: Record<string, string>
}

export const imagesApi = {
  list: (hostId?: string) => 
    api.get<Image[]>('/images', { params: { host_id: hostId } }),
  
  get: (id: string, hostId?: string) => 
    api.get<Image>(`/images/${id}`, { params: { host_id: hostId } }),
  
  pull: (data: ImagePullRequest, hostId?: string) => 
    api.post<{ task_id: string; message: string }>('/images/pull', data, { params: { host_id: hostId } }),
  
  remove: (id: string, force = false, hostId?: string) => 
    api.delete(`/images/${id}`, { params: { force, host_id: hostId } }),
  
  history: (id: string, hostId?: string) => 
    api.get<{
      image_id: string
      history: Array<{
        created: string
        created_by: string
        size: number
        comment: string
      }>
    }>(`/images/${id}/history`, { params: { host_id: hostId } }),
  
  prune: (hostId?: string) => 
    api.post<{
      message: string
      images_deleted: string[]
      space_reclaimed: number
    }>('/images/prune', null, { params: { host_id: hostId } }),
}