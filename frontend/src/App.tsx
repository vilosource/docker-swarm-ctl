import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import LayoutFull from '@/components/layout/LayoutFull'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Containers from '@/pages/Containers'
import ContainerDetails from '@/pages/ContainerDetails'
import Images from '@/pages/Images'
import Users from '@/pages/Users'
import Profile from '@/pages/Profile'

function App() {
  const isAuthenticated = useAuthStore((state) => !!state.token)

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
      
      <Route element={<ProtectedRoute />}>
        <Route element={<LayoutFull />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/containers" element={<Containers />} />
          <Route path="/containers/:id" element={<ContainerDetails />} />
          <Route path="/images" element={<Images />} />
          <Route path="/users" element={<Users />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Route>
      
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App