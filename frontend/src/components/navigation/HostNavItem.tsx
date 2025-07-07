import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { DockerHost } from '@/types'
import { truncateHostname } from '@/utils/format'

interface HostNavItemProps {
  host: DockerHost
}

interface NavSubItem {
  name: string
  href: string
  icon: string
}

export default function HostNavItem({ host }: HostNavItemProps) {
  const location = useLocation()
  
  console.log('[HostNavItem] Rendering host:', host)
  
  const subItems: NavSubItem[] = [
    { name: 'Containers', href: `/hosts/${host.id}/containers`, icon: 'mdi mdi-docker' },
    { name: 'Images', href: `/hosts/${host.id}/images`, icon: 'mdi mdi-layers' },
    { name: 'Networks', href: `/hosts/${host.id}/networks`, icon: 'mdi mdi-lan' },
    { name: 'Volumes', href: `/hosts/${host.id}/volumes`, icon: 'mdi mdi-database' },
    { name: 'System', href: `/hosts/${host.id}/system`, icon: 'mdi mdi-information-outline' },
  ]
  
  // Check if any sub-item is active (current page is within this host's section)
  const isActive = location.pathname.startsWith(`/hosts/${host.id}`)
  
  // Initialize expansion state as collapsed by default
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Update expansion state when location changes
  useEffect(() => {
    // Auto-expand if the current page is within this host's section
    setIsExpanded(isActive)
  }, [isActive])
  
  // Get host icon based on type
  const getHostIcon = () => {
    switch (host.host_type) {
      case 'swarm_manager':
        return host.is_leader ? 'mdi mdi-crown' : 'mdi mdi-shield-star'
      case 'swarm_worker':
        return 'mdi mdi-worker'
      default:
        return 'mdi mdi-server'
    }
  }
  
  // Get host status color
  const getStatusColor = () => {
    switch (host.status) {
      case 'healthy':
        return 'text-success'
      case 'unhealthy':
        return 'text-danger'
      case 'pending':
        return 'text-warning'
      default:
        return 'text-secondary'
    }
  }
  
  return (
    <li className={isActive ? 'menuitem-active' : ''}>
      <a
        href="#"
        className={`has-arrow ${isActive ? 'active' : ''} ${!isExpanded ? 'collapsed' : ''}`}
        onClick={(e) => {
          e.preventDefault()
          // Toggle expansion state
          setIsExpanded(!isExpanded)
        }}
        aria-expanded={isExpanded}
        title={host.name}
      >
        <i className={getHostIcon()}></i>
        <span>
          {host.display_name || truncateHostname(host.name)}
          <i className={`mdi mdi-circle ${getStatusColor()} font-10 ms-2`} style={{ fontSize: '8px' }}></i>
        </span>
      </a>
      <ul 
        className={`nav-second-level ${isExpanded ? 'mm-show' : 'mm-collapse'}`}
        style={{
          display: isExpanded ? 'block' : 'none',
          overflow: 'hidden',
          transition: 'all 0.3s ease'
        }}
      >
        {subItems.map((item) => {
          const itemActive = location.pathname === item.href
          return (
            <li key={item.name} className={itemActive ? 'menuitem-active' : ''}>
              <Link to={item.href} className={itemActive ? 'active' : ''}>
                <i className={item.icon}></i>
                <span>{item.name}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </li>
  )
}