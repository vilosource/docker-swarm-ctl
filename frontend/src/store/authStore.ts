import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User, TokenPair } from '@/types'
import { api } from '@/api/client'
import { authApi } from '@/api/auth'

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<void>
  setUser: (user: User | null) => void
  setTokens: (tokens: TokenPair | null) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      
      login: async (email: string, password: string) => {
        const response = await authApi.login({ email, password })
        const tokens = response.data
        
        // Set tokens in store
        set({
          token: tokens.access_token,
          refreshToken: tokens.refresh_token,
        })
        
        // Configure axios with token
        api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`
        
        // Fetch user info
        const userResponse = await api.get<User>('/users/me')
        set({ user: userResponse.data })
      },
      
      logout: async () => {
        const { refreshToken } = get()
        
        if (refreshToken) {
          try {
            await authApi.logout(refreshToken)
          } catch (error) {
            console.error('Logout error:', error)
          }
        }
        
        // Clear store
        set({
          user: null,
          token: null,
          refreshToken: null,
        })
        
        // Clear axios header
        delete api.defaults.headers.common['Authorization']
      },
      
      refreshTokens: async () => {
        const { refreshToken } = get()
        
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }
        
        const response = await authApi.refreshToken(refreshToken)
        const newToken = response.data.access_token
        
        // Update token in store
        set({ token: newToken })
        
        // Update axios header
        api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
      },
      
      setUser: (user) => set({ user }),
      
      setTokens: (tokens) => {
        if (tokens) {
          set({
            token: tokens.access_token,
            refreshToken: tokens.refresh_token,
          })
          api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`
        } else {
          set({
            token: null,
            refreshToken: null,
          })
          delete api.defaults.headers.common['Authorization']
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
)

// Initialize axios with stored token
const token = useAuthStore.getState().token
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}