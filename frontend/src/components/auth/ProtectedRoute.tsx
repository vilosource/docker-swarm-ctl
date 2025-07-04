import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => !!state.token)
  
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}