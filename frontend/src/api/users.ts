import { api } from './client'
import { User, PaginatedResponse } from '@/types'

export interface UserCreateRequest {
  email: string
  username: string
  full_name: string
  password: string
  role?: 'admin' | 'operator' | 'viewer'
  is_active?: boolean
}

export interface UserUpdateRequest {
  email?: string
  username?: string
  full_name?: string
  password?: string
  role?: 'admin' | 'operator' | 'viewer'
  is_active?: boolean
}

export const usersApi = {
  list: (skip = 0, limit = 100) => 
    api.get<PaginatedResponse<User>>('/users', { params: { skip, limit } }),
  
  get: (id: string) => 
    api.get<User>(`/users/${id}`),
  
  me: () => 
    api.get<User>('/users/me'),
  
  create: (data: UserCreateRequest) => 
    api.post<User>('/users', data),
  
  update: (id: string, data: UserUpdateRequest) => 
    api.put<User>(`/users/${id}`, data),
  
  delete: (id: string) => 
    api.delete(`/users/${id}`),
}