import axios from 'axios'
import { LoginRequest, TokenPair } from '@/types'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Use a separate axios instance for auth to avoid circular dependency
const authClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const authApi = {
  login: (data: LoginRequest) => {
    const formData = new URLSearchParams()
    formData.append('username', data.email)
    formData.append('password', data.password)
    
    return authClient.post<TokenPair>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },
  
  logout: (refreshToken: string) => 
    authClient.post('/auth/logout', { refresh_token: refreshToken }),
  
  refreshToken: (refreshToken: string) => 
    authClient.post<{ access_token: string; token_type: string }>('/auth/refresh', { 
      refresh_token: refreshToken 
    }),
}