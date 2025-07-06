import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/authStore'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    console.log('[API Request]', {
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      params: config.params,
      headers: config.headers,
      timestamp: new Date().toISOString()
    })
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => {
    console.log('[API Response]', {
      method: response.config.method?.toUpperCase(),
      url: response.config.url,
      status: response.status,
      statusText: response.statusText,
      data: response.data,
      timestamp: new Date().toISOString()
    })
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    console.error('[API Response Error]', {
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
      timestamp: new Date().toISOString()
    })
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        await useAuthStore.getState().refreshTokens()
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed, logout user
        await useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)