import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import Layout from '@/components/layout/Layout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Containers from '@/pages/Containers'
import ContainerDetails from '@/pages/ContainerDetails'
import Images from '@/pages/Images'
import Volumes from '@/pages/Volumes'
import Networks from '@/pages/Networks'
import Users from '@/pages/Users'
import Hosts from '@/pages/Hosts'
import Profile from '@/pages/Profile'
import SystemStats from '@/pages/SystemStats'
import Events from '@/pages/Events'
import HostContainers from '@/pages/HostContainers'
import HostImages from '@/pages/HostImages'
import HostVolumes from '@/pages/HostVolumes'
import HostNetworks from '@/pages/HostNetworks'
import HostSystem from '@/pages/HostSystem'

function App() {
  const isAuthenticated = useAuthStore((state) => !!state.token)

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
      
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/system-stats" element={<SystemStats />} />
          <Route path="/containers" element={<Containers />} />
          <Route path="/containers/:id" element={<ContainerDetails />} />
          <Route path="/hosts/:hostId/containers/:id" element={<ContainerDetails />} />
          <Route path="/images" element={<Images />} />
          <Route path="/volumes" element={<Volumes />} />
          <Route path="/networks" element={<Networks />} />
          <Route path="/events" element={<Events />} />
          <Route path="/users" element={<Users />} />
          <Route path="/hosts" element={<Hosts />} />
          <Route path="/hosts/:hostId/containers" element={<HostContainers />} />
          <Route path="/hosts/:hostId/images" element={<HostImages />} />
          <Route path="/hosts/:hostId/volumes" element={<HostVolumes />} />
          <Route path="/hosts/:hostId/networks" element={<HostNetworks />} />
          <Route path="/hosts/:hostId/system" element={<HostSystem />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Route>
      
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App