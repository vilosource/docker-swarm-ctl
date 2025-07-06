import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import LayoutSimple from '@/components/layout/LayoutSimple'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Containers from '@/pages/Containers'
import ContainerDetails from '@/pages/ContainerDetails'
import Images from '@/pages/Images'
import Users from '@/pages/Users'
import Hosts from '@/pages/Hosts'
import Profile from '@/pages/Profile'
import SystemStats from '@/pages/SystemStats'
import HostContainers from '@/pages/HostContainers'
import HostImages from '@/pages/HostImages'
import HostSystem from '@/pages/HostSystem'

function App() {
  const isAuthenticated = useAuthStore((state) => !!state.token)

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
      
      <Route element={<ProtectedRoute />}>
        <Route element={<LayoutSimple />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/system-stats" element={<SystemStats />} />
          <Route path="/containers" element={<Containers />} />
          <Route path="/containers/:id" element={<ContainerDetails />} />
          <Route path="/images" element={<Images />} />
          <Route path="/users" element={<Users />} />
          <Route path="/hosts" element={<Hosts />} />
          <Route path="/hosts/:hostId/containers" element={<HostContainers />} />
          <Route path="/hosts/:hostId/images" element={<HostImages />} />
          <Route path="/hosts/:hostId/system" element={<HostSystem />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Route>
      
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App