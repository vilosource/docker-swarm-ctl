import { useState, useEffect } from 'react'
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { hostsApi } from '@/api/hosts'
import HostNavItem from '@/components/navigation/HostNavItem'
import { useSidebarToggle } from '@/hooks/useSidebarToggle'

const staticNavigation = [
  { 
    name: 'Dashboard', 
    href: '/', 
    icon: 'mdi mdi-view-dashboard',
    exact: true
  },
]

const adminNavigation = [
  { 
    name: 'Host Management', 
    href: '/hosts', 
    icon: 'mdi mdi-server-network'
  },
  { 
    name: 'Users', 
    href: '/users', 
    icon: 'mdi mdi-account-multiple'
  },
]

export default function Layout() {
  console.log('[Layout] Component rendering')
  
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { toggleSidebar } = useSidebarToggle()
  const [expandedSections, setExpandedSections] = useState<string[]>(['all-hosts'])
  
  // Fetch hosts for navigation
  const { data: hostsData, error: hostsError, isLoading: hostsLoading, isError: hostsIsError } = useQuery({
    queryKey: ['hosts', 'navigation'],
    queryFn: () => hostsApi.list({ active_only: true }),
    staleTime: 30000, // Refresh every 30 seconds
    onSuccess: (data) => {
      console.log('[Layout] Hosts query success:', data)
    },
    onError: (error) => {
      console.error('[Layout] Hosts query error:', error)
    },
  })
  
  // Debug logging
  console.log('[Layout] Hosts query state:', {
    hostsData,
    hostsError,
    hostsLoading,
    hostsIsError,
    queryKey: ['hosts', 'navigation'],
    timestamp: new Date().toISOString()
  })
  
  const hosts = hostsData?.items || []
  
  // Simple debug log
  if (hostsData) {
    console.log('[Layout] hostsData exists:', hostsData)
    console.log('[Layout] hostsData.items:', hostsData.items)
    console.log('[Layout] hosts array:', hosts)
  }
  console.log('[Layout] Processed hosts array:', hosts)
  
  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }
  
  const isAdmin = user?.role === 'admin'
  
  // Initialize theme
  useEffect(() => {
    
    // Initialize theme if app.js is loaded
    if (window.$ && window.App) {
      window.App.init()
    }
  }, [])
  
  return (
    <div id="wrapper">
      {/* Topbar Start */}
      <div className="navbar-custom">
        <div className="container-fluid">
          <ul className="list-unstyled topnav-menu float-end mb-0">
            {/* Dark/Light Mode Toggle */}
            <li className="d-none d-md-inline-block">
              <a 
                className="nav-link dropdown-toggle arrow-none waves-effect waves-light" 
                id="light-dark-mode" 
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  document.body.classList.toggle('dark')
                }}
              >
                <i className="fe-moon noti-icon"></i>
              </a>
            </li>
            
            {/* Fullscreen Toggle */}
            <li className="dropdown d-none d-lg-inline-block">
              <a 
                className="nav-link dropdown-toggle arrow-none waves-effect waves-light" 
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen()
                  } else {
                    document.exitFullscreen()
                  }
                }}
              >
                <i className="fe-maximize noti-icon"></i>
              </a>
            </li>
            
            {/* User Dropdown */}
            <li className="dropdown notification-list topbar-dropdown">
              <a className="nav-link dropdown-toggle nav-user me-0" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                <img src="/assets/images/users/avatar-1.jpg" alt="user-image" className="rounded-circle" height="32" />
                <span className="pro-user-name ms-1">
                  {user?.username} <i className="mdi mdi-chevron-down"></i>
                </span>
              </a>
              <div className="dropdown-menu dropdown-menu-end profile-dropdown">
                {/* User Details */}
                <div className="dropdown-header noti-title">
                  <h6 className="text-overflow m-0">Welcome!</h6>
                </div>
                
                <Link to="/profile" className="dropdown-item notify-item">
                  <i className="fe-user"></i>
                  <span>My Account</span>
                </Link>
                
                <div className="dropdown-divider"></div>
                
                <a href="#" className="dropdown-item notify-item" onClick={handleLogout}>
                  <i className="fe-log-out"></i>
                  <span>Logout</span>
                </a>
              </div>
            </li>
          </ul>
          
          {/* LOGO */}
          <div className="logo-box">
            <Link to="/" className="logo logo-dark text-center">
              <span className="logo-sm">
                <i className="mdi mdi-docker" style={{ fontSize: '24px' }}></i>
              </span>
              <span className="logo-lg">
                <i className="mdi mdi-docker me-2" style={{ fontSize: '24px' }}></i>
                <span style={{ fontSize: '18px', fontWeight: 'bold' }}>Docker CTL</span>
              </span>
            </Link>
          </div>
          
          <ul className="list-unstyled topnav-menu topnav-menu-left mb-0">
            <li>
              <button 
                className="button-menu-mobile waves-effect waves-light"
                type="button"
                onClick={toggleSidebar}
              >
                <i className="fe-menu"></i>
              </button>
            </li>
          </ul>
          
          <div className="clearfix"></div>
        </div>
      </div>
      {/* end Topbar */}
      
      {/* ========== Left Sidebar Start ========== */}
      <div className="left-side-menu">
        <div className="h-100" data-simplebar>
          {/* Logo box */}
          <div className="logo-box">
            <Link to="/" className="logo logo-light text-center">
              <span className="logo-sm">
                <i className="mdi mdi-docker" style={{ fontSize: '24px' }}></i>
              </span>
              <span className="logo-lg">
                <i className="mdi mdi-docker me-2" style={{ fontSize: '24px' }}></i>
                <span style={{ fontSize: '18px', fontWeight: 'bold' }}>Docker CTL</span>
              </span>
            </Link>
          </div>
          
          {/* User box */}
          <div className="user-box text-center">
            <div className="dropdown">
              <a href="#" className="user-name dropdown-toggle h5 mt-2 mb-1 d-block">
                {user?.username}
              </a>
            </div>
            <p className="text-muted left-user-info">{user?.role}</p>
          </div>
          
          {/* Sidebar */}
          <div id="sidebar-menu">
            <ul id="side-menu">
              {/* Main Navigation */}
              <li className="menu-title">Navigation</li>
              
              {staticNavigation.map((item) => {
                const isActive = item.exact 
                  ? location.pathname === item.href
                  : location.pathname.startsWith(item.href)
                
                return (
                  <li key={item.name} className={isActive ? 'menuitem-active' : ''}>
                    <Link to={item.href} className={isActive ? 'active' : ''}>
                      <i className={item.icon}></i>
                      <span> {item.name} </span>
                    </Link>
                  </li>
                )
              })}
              
              {/* All Hosts Section */}
              <li className="menu-title mt-2">Resources</li>
              <li className={location.pathname.startsWith('/containers') || location.pathname.startsWith('/images') || location.pathname.startsWith('/volumes') || location.pathname.startsWith('/networks') || location.pathname.startsWith('/events') ? 'menuitem-active' : ''}>
                <a
                  href="#"
                  className={`has-arrow ${expandedSections.includes('all-hosts') ? '' : 'collapsed'}`}
                  onClick={(e) => {
                    e.preventDefault()
                    setExpandedSections(prev => 
                      prev.includes('all-hosts') 
                        ? prev.filter(s => s !== 'all-hosts')
                        : [...prev, 'all-hosts']
                    )
                  }}
                  aria-expanded={expandedSections.includes('all-hosts')}
                >
                  <i className="mdi mdi-view-grid"></i>
                  <span>All Hosts</span>
                </a>
                <ul className={`nav-second-level ${expandedSections.includes('all-hosts') ? 'mm-show' : 'mm-collapse'}`}>
                  <li className={location.pathname === '/containers' ? 'menuitem-active' : ''}>
                    <Link to="/containers" className={location.pathname === '/containers' ? 'active' : ''}>
                      <i className="mdi mdi-docker"></i>
                      <span>Containers</span>
                    </Link>
                  </li>
                  <li className={location.pathname === '/images' ? 'menuitem-active' : ''}>
                    <Link to="/images" className={location.pathname === '/images' ? 'active' : ''}>
                      <i className="mdi mdi-layers"></i>
                      <span>Images</span>
                    </Link>
                  </li>
                  <li className={location.pathname === '/volumes' ? 'menuitem-active' : ''}>
                    <Link to="/volumes" className={location.pathname === '/volumes' ? 'active' : ''}>
                      <i className="mdi mdi-database"></i>
                      <span>Volumes</span>
                    </Link>
                  </li>
                  <li className={location.pathname === '/networks' ? 'menuitem-active' : ''}>
                    <Link to="/networks" className={location.pathname === '/networks' ? 'active' : ''}>
                      <i className="mdi mdi-lan"></i>
                      <span>Networks</span>
                    </Link>
                  </li>
                  <li className={location.pathname === '/events' ? 'menuitem-active' : ''}>
                    <Link to="/events" className={location.pathname === '/events' ? 'active' : ''}>
                      <i className="mdi mdi-pulse"></i>
                      <span>Events</span>
                    </Link>
                  </li>
                </ul>
              </li>
              
              {/* Swarm Section */}
              <li className={location.pathname.includes('/swarm') || location.pathname.includes('/nodes') || location.pathname.includes('/services') || location.pathname.includes('/secrets-configs') ? 'menuitem-active' : ''}>
                <a
                  href="#"
                  className={`has-arrow ${expandedSections.includes('swarm') ? '' : 'collapsed'}`}
                  onClick={(e) => {
                    e.preventDefault()
                    setExpandedSections(prev => 
                      prev.includes('swarm') 
                        ? prev.filter(s => s !== 'swarm')
                        : [...prev, 'swarm']
                    )
                  }}
                  aria-expanded={expandedSections.includes('swarm')}
                >
                  <i className="mdi mdi-cloud-braces"></i>
                  <span>Swarm</span>
                </a>
                <ul className={`nav-second-level ${expandedSections.includes('swarm') ? 'mm-show' : 'mm-collapse'}`}>
                  <li className={location.pathname === '/swarms' ? 'menuitem-active' : ''}>
                    <Link to="/swarms" className={location.pathname === '/swarms' ? 'active' : ''}>
                      <i className="mdi mdi-view-dashboard-outline"></i>
                      <span>Overview</span>
                    </Link>
                  </li>
                  {hosts.length > 0 && hosts[0]?.id && (
                    <>
                      <li className={location.pathname.includes('/nodes') ? 'menuitem-active' : ''}>
                        <Link to={`/hosts/${hosts[0].id}/nodes`} className={location.pathname.includes('/nodes') ? 'active' : ''}>
                          <i className="mdi mdi-server-network"></i>
                          <span>Nodes</span>
                        </Link>
                      </li>
                      <li className={location.pathname.includes('/services') ? 'menuitem-active' : ''}>
                        <Link to={`/hosts/${hosts[0].id}/services`} className={location.pathname.includes('/services') ? 'active' : ''}>
                          <i className="mdi mdi-cogs"></i>
                          <span>Services</span>
                        </Link>
                      </li>
                      <li className={location.pathname.includes('/secrets-configs') ? 'menuitem-active' : ''}>
                        <Link to={`/hosts/${hosts[0].id}/secrets-configs`} className={location.pathname.includes('/secrets-configs') ? 'active' : ''}>
                          <i className="mdi mdi-key-variant"></i>
                          <span>Secrets & Configs</span>
                        </Link>
                      </li>
                    </>
                  )}
                  {(!hosts || hosts.length === 0) && (
                    <li className="text-muted text-center py-2">
                      <small>No hosts available</small>
                    </li>
                  )}
                </ul>
              </li>
              
              {/* Individual Hosts */}
              {console.log('[Layout] Rendering hosts section, hosts.length:', hosts.length)}
              {/* Show loading state */}
              {hostsLoading && (
                <li className="text-muted text-center py-2">
                  <small>Loading hosts...</small>
                </li>
              )}
              {/* Show error state */}
              {hostsIsError && (
                <li className="text-danger text-center py-2">
                  <small>Error loading hosts: {(hostsError as any)?.message || 'Unknown error'}</small>
                </li>
              )}
              {/* Show hosts if available */}
              {!hostsLoading && !hostsIsError && hosts.length > 0 && (
                <>
                  <li className="menu-title mt-2">Docker Hosts</li>
                  {hosts.map((host) => {
                    console.log('[Layout] Rendering host:', host)
                    return <HostNavItem key={host.id} host={host} />
                  })}
                </>
              )}
              {/* Show empty state */}
              {!hostsLoading && !hostsIsError && hosts.length === 0 && (
                <li className="text-muted text-center py-2">
                  <small>No hosts configured</small>
                </li>
              )}
              
              {/* Admin Section */}
              {isAdmin && (
                <>
                  <li className="menu-title mt-2">Administration</li>
                  {adminNavigation.map((item) => {
                    const isActive = location.pathname.startsWith(item.href)
                    
                    return (
                      <li key={item.name} className={isActive ? 'menuitem-active' : ''}>
                        <Link to={item.href} className={isActive ? 'active' : ''}>
                          <i className={item.icon}></i>
                          <span> {item.name} </span>
                        </Link>
                      </li>
                    )
                  })}
                </>
              )}
            </ul>
          </div>
          {/* End Sidebar */}
          
          <div className="clearfix"></div>
        </div>
      </div>
      {/* Left Sidebar End */}
      
      {/* ============================================================== */}
      {/* Start Page Content here */}
      {/* ============================================================== */}
      
      <div className="content-page">
        <div className="content">
          {/* Start Content*/}
          <div className="container-fluid">
            <Outlet />
          </div>
        </div>
        
        {/* Footer Start */}
        <footer className="footer">
          <div className="container-fluid">
            <div className="row">
              <div className="col-md-6">
                {new Date().getFullYear()} &copy; Docker Control Platform
              </div>
            </div>
          </div>
        </footer>
        {/* end Footer */}
      </div>
      
      {/* ============================================================== */}
      {/* End Page content */}
      {/* ============================================================== */}
    </div>
  )
}