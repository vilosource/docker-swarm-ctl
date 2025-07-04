import { api } from './client'
import { Image } from '@/types'

export interface ImagePullRequest {
  repository: string
  tag?: string
  auth_config?: Record<string, string>
}

export const imagesApi = {
  list: () => 
    api.get<Image[]>('/images'),
  
  get: (id: string) => 
    api.get<Image>(`/images/${id}`),
  
  pull: (data: ImagePullRequest) => 
    api.post<{ task_id: string; message: string }>('/images/pull', data),
  
  remove: (id: string, force = false) => 
    api.delete(`/images/${id}`, { params: { force } }),
  
  history: (id: string) => 
    api.get<{
      image_id: string
      history: Array<{
        created: string
        created_by: string
        size: number
        comment: string
      }>
    }>(`/images/${id}/history`),
  
  prune: () => 
    api.post<{
      message: string
      images_deleted: string[]
      space_reclaimed: number
    }>('/images/prune'),
}