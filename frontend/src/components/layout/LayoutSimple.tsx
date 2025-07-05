import React from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useSidebarToggle } from '@/hooks/useSidebarToggle'

const navigation = [
  { 
    name: 'Dashboard', 
    href: '/', 
    icon: 'mdi mdi-view-dashboard',
    exact: true
  },
  { 
    name: 'System Stats', 
    href: '/system-stats', 
    icon: 'mdi mdi-chart-line'
  },
  { 
    name: 'Containers', 
    href: '/containers', 
    icon: 'mdi mdi-docker'
  },
  { 
    name: 'Images', 
    href: '/images', 
    icon: 'mdi mdi-layers'
  },
  { 
    name: 'Users', 
    href: '/users', 
    icon: 'mdi mdi-account-multiple',
    adminOnly: true 
  },
];

const LayoutSimple: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { toggleSidebar, isCondensed } = useSidebarToggle()
  
  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }
  
  const isAdmin = user?.role === 'admin'
  
  return (
    <>
      <div id="wrapper">
        {/* Topbar Start */}
        <div className="navbar-custom">
          <div className="container-fluid">
            <ul className="list-unstyled topnav-menu float-end mb-0">
              <li className="dropdown notification-list topbar-dropdown">
                <a className="nav-link dropdown-toggle nav-user me-0 waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  <img src="assets/images/users/avatar-1.jpg" alt="user-image" className="rounded-circle" />
                  <span className="pro-user-name ms-1">
                    {user?.username} <i className="mdi mdi-chevron-down"></i>
                  </span>
                </a>
                <div className="dropdown-menu dropdown-menu-end profile-dropdown ">
                  <div className="dropdown-header noti-title">
                    <h6 className="text-overflow m-0">Welcome !</h6>
                  </div>
                  <Link to="/profile" className="dropdown-item notify-item">
                    <i className="ri-account-circle-line"></i>
                    <span>My Account</span>
                  </Link>
                  <div className="dropdown-divider"></div>
                  <a href="#" className="dropdown-item notify-item" onClick={(e) => { e.preventDefault(); handleLogout(); }}>
                    <i className="ri-logout-box-line"></i>
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

            <ul className="list-unstyled topnav-menu topnav-menu-left m-0">
              <li>
                <button 
                  className="button-menu-mobile waves-effect waves-light"
                  onClick={toggleSidebar}
                >
                  <i className="fe-menu"></i>
                </button>
              </li>
            </ul>
            <div className="clearfix"></div>
          </div>
        </div>
        {/* Topbar End */}

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
              <img src="assets/images/users/avatar-1.jpg" alt="user-img" title={user?.username} className="rounded-circle avatar-md" />
              <div className="dropdown">
                <a href="#" className="text-reset h5 mt-2 mb-1 d-block">{user?.username}</a>
              </div>
              <p className="text-reset">{user?.role}</p>
            </div>

            {/* Sidemenu */}
            <div id="sidebar-menu">
              <ul id="side-menu">
                <li className="menu-title">Navigation</li>
              
                {navigation.map((item) => {
                  if (item.adminOnly && !isAdmin) return null
                  
                  const isActive = item.exact 
                    ? location.pathname === item.href
                    : location.pathname.startsWith(item.href)
                  
                  return (
                    <li key={item.name} className={isActive ? 'menuitem-active' : ''}>
                      <Link 
                        to={item.href} 
                        className={isActive ? 'active' : ''}
                      >
                        <i className={item.icon}></i>
                        <span> {item.name} </span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
            {/* End Sidebar */}

            <div className="clearfix"></div>
          </div>
          {/* Sidebar -left */}
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
            {/* container-fluid */}
          </div>
          {/* content */}

          {/* Footer Start */}
          <footer className="footer">
            <div className="container-fluid">
              <div className="row">
                <div className="col-md-6">
                  2025 &copy; Docker Control Platform
                </div>
                <div className="col-md-6">
                  <div className="text-md-end footer-links d-none d-sm-block">
                    <Link to="/profile">Profile</Link>
                  </div>
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
      {/* END wrapper */}
    </>
  );
};

export default LayoutSimple;