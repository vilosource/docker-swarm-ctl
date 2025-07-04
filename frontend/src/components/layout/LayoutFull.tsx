import React from 'react';
import { useState, useEffect } from 'react'
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

const navigation = [
  { 
    name: 'Dashboard', 
    href: '/', 
    icon: 'mdi mdi-view-dashboard',
    exact: true
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

const LayoutFull: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  
  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }
  
  const isAdmin = user?.role === 'admin'
  
  // Initialize theme and handle events
  useEffect(() => {
    // Ensure sidebar is hidden on mobile by default
    if (window.innerWidth < 992) {
      document.body.classList.remove('sidebar-enable')
      // Remove any existing backdrop
      const existingBackdrop = document.getElementById('custom-backdrop')
      if (existingBackdrop) {
        existingBackdrop.remove()
      }
    }
    // Function to show backdrop for mobile
    const showBackdrop = () => {
      const existingBackdrop = document.getElementById('custom-backdrop')
      if (!existingBackdrop) {
        const backdrop = document.createElement('div')
        backdrop.id = 'custom-backdrop'
        backdrop.className = 'offcanvas-backdrop fade show'
        backdrop.style.zIndex = '1050'
        document.body.appendChild(backdrop)
        
        // Click on backdrop to close menu
        backdrop.addEventListener('click', () => {
          document.body.classList.remove('sidebar-enable')
          hideBackdrop()
        })
      }
    }
    
    // Function to hide backdrop
    const hideBackdrop = () => {
      const backdrop = document.getElementById('custom-backdrop')
      if (backdrop) {
        backdrop.remove()
      }
    }
    
    // Handle mobile menu toggle
    const handleMenuToggle = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('.button-menu-mobile')) {
        e.preventDefault()
        
        if (window.innerWidth < 992) {
          // Mobile - toggle sidebar-enable and show/hide backdrop
          const isSidebarOpen = document.body.classList.contains('sidebar-enable')
          
          if (isSidebarOpen) {
            document.body.classList.remove('sidebar-enable')
            hideBackdrop()
          } else {
            document.body.classList.add('sidebar-enable')
            showBackdrop()
          }
        } else {
          // Desktop - toggle left-side-menu-condensed
          document.body.classList.toggle('left-side-menu-condensed')
        }
      }
    }
    
    // Handle window resize
    const handleResize = () => {
      if (window.innerWidth >= 992) {
        // Remove mobile-specific classes on desktop
        document.body.classList.remove('sidebar-enable')
        hideBackdrop()
      }
    }
    
    // Handle theme toggle
    const handleThemeToggle = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('#light-dark-mode')) {
        e.preventDefault()
        document.body.classList.toggle('dark')
      }
    }
    
    // Handle fullscreen toggle
    const handleFullscreenToggle = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('[data-toggle="fullscreen"]')) {
        e.preventDefault()
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen()
        } else {
          document.exitFullscreen()
        }
      }
    }
    
    // Add event listeners
    document.addEventListener('click', handleMenuToggle)
    document.addEventListener('click', handleThemeToggle)
    document.addEventListener('click', handleFullscreenToggle)
    window.addEventListener('resize', handleResize)
    
    // Initialize Bootstrap dropdowns if needed
    if (typeof window !== 'undefined' && window.bootstrap) {
      // Bootstrap is loaded
    }
    
    return () => {
      document.removeEventListener('click', handleMenuToggle)
      document.removeEventListener('click', handleThemeToggle)
      document.removeEventListener('click', handleFullscreenToggle)
      window.removeEventListener('resize', handleResize)
      hideBackdrop() // Clean up backdrop on unmount
    }
  }, [])
  
  return (
    <>
      {/* Begin page */}
      <div id="wrapper">
        {/* Topbar Start */}
        <div className="navbar-custom">
          <div className="container-fluid">
            <ul className="list-unstyled topnav-menu float-end mb-0">
              <li className="d-none d-lg-block">
                <form className="app-search">
                  <div className="app-search-box dropdown">
                    <div className="input-group">
                      <input type="search" className="form-control" placeholder="Search..." id="top-search" />
                      <button className="btn" type="submit">
                        <i className="fe-search"></i>
                      </button>
                    </div>
                    <div className="dropdown-menu dropdown-lg" id="search-dropdown">
                      {/* item*/}
                      <div className="dropdown-header noti-title">
                        <h5 className="text-overflow mb-2">Found <span className="text-danger">09</span> results</h5>
                      </div>
                      {/* item*/}
                      <a href="javascript:void(0);" className="dropdown-item notify-item">
                        <i className="fe-home me-1"></i>
                        <span>Analytics Report</span>
                      </a>
                      {/* item*/}
                      <a href="javascript:void(0);" className="dropdown-item notify-item">
                        <i className="fe-aperture me-1"></i>
                        <span>How can I help you?</span>
                      </a>
                      {/* item*/}
                      <a href="javascript:void(0);" className="dropdown-item notify-item">
                        <i className="fe-settings me-1"></i>
                        <span>User profile settings</span>
                      </a>
                      {/* item*/}
                      <div className="dropdown-header noti-title">
                        <h6 className="text-overflow mb-2 text-uppercase">Users</h6>
                      </div>
                      <div className="notification-list">
                        {/* item*/}
                        <a href="javascript:void(0);" className="dropdown-item notify-item">
                          <div className="d-flex">
                            <img className="d-flex me-2 rounded-circle" src="assets/images/users/avatar-2.jpg" alt="Generic placeholder image" height="32" />
                            <div>
                              <h5 className="m-0 font-14">Erwin E. Brown</h5>
                              <span className="font-12 mb-0">UI Designer</span>
                            </div>
                          </div>
                        </a>
                        {/* item*/}
                        <a href="javascript:void(0);" className="dropdown-item notify-item">
                          <div className="d-flex">
                            <img className="d-flex me-2 rounded-circle" src="assets/images/users/avatar-5.jpg" alt="Generic placeholder image" height="32" />
                            <div>
                              <h5 className="m-0 font-14">Jacob Deo</h5>
                              <span className="font-12 mb-0">Developer</span>
                            </div>
                          </div>
                        </a>
                      </div>
                    </div>
                  </div>
                </form>
              </li>

              <li className="dropdown d-inline-block d-lg-none">
                <a className="nav-link dropdown-toggle arrow-none waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  <i className="fe-search noti-icon"></i>
                </a>
                <div className="dropdown-menu dropdown-lg dropdown-menu-end p-0">
                  <form className="p-3">
                    <input type="text" className="form-control" placeholder="Search ..." aria-label="Search" />
                  </form>
                </div>
              </li>

              <li className="d-none d-md-inline-block">
                <a className="nav-link dropdown-toggle arrow-none waves-effect waves-light" id="light-dark-mode" href="#">
                  <i className="fe-moon noti-icon"></i>
                </a>
              </li>

              <li className="dropdown d-none d-lg-inline-block">
                <a className="nav-link dropdown-toggle arrow-none waves-effect waves-light" data-toggle="fullscreen" href="#">
                  <i className="fe-maximize noti-icon"></i>
                </a>
              </li>

              <li className="dropdown d-none d-lg-inline-block topbar-dropdown">
                <a className="nav-link dropdown-toggle arrow-none waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  <i className="fe-grid noti-icon"></i>
                </a>
                <div className="dropdown-menu dropdown-lg dropdown-menu-end p-0">
                  <div className="p-2">
                    <div className="row g-0">
                      <div className="col">
                        <a className="dropdown-icon-item" href="#">
                          <img src="assets/images/brands/github.png" alt="Github" />
                          <span>GitHub</span>
                        </a>
                      </div>
                      <div className="col">
                        <a className="dropdown-icon-item" href="#">
                          <img src="assets/images/brands/dribbble.png" alt="dribbble" />
                          <span>Dribbble</span>
                        </a>
                      </div>
                      <div className="col">
                        <a className="dropdown-icon-item" href="#">
                          <img src="assets/images/brands/slack.png" alt="slack" />
                          <span>Slack</span>
                        </a>
                      </div>
                    </div>

                    <div className="row g-0">
                      <div className="col">
                        <a className="dropdown-icon-item" href="#">
                          <img src="assets/images/brands/g-suite.png" alt="G Suite" />
                          <span>G Suite</span>
                        </a>
                      </div>
                      <div className="col">
                        <a className="dropdown-icon-item" href="#">
                          <img src="assets/images/brands/bitbucket.png" alt="bitbucket" />
                          <span>Bitbucket</span>
                        </a>
                      </div>
                      <div className="col">
                        <a className="dropdown-icon-item" href="#">
                          <img src="assets/images/brands/dropbox.png" alt="dropbox" />
                          <span>Dropbox</span>
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </li>

              <li className="dropdown d-none d-lg-inline-block topbar-dropdown">
                <a className="nav-link dropdown-toggle arrow-none waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  <img src="assets/images/flags/us.jpg" alt="user-image" height="14" />
                </a>
                <div className="dropdown-menu dropdown-menu-end">
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <img src="assets/images/flags/germany.jpg" alt="user-image" className="me-1" height="12" /> <span className="align-middle">German</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <img src="assets/images/flags/italy.jpg" alt="user-image" className="me-1" height="12" /> <span className="align-middle">Italian</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <img src="assets/images/flags/spain.jpg" alt="user-image" className="me-1" height="12" /> <span className="align-middle">Spanish</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <img src="assets/images/flags/russia.jpg" alt="user-image" className="me-1" height="12" /> <span className="align-middle">Russian</span>
                  </a>
                </div>
              </li>

              <li className="dropdown notification-list topbar-dropdown">
                <a className="nav-link dropdown-toggle waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  <i className="fe-bell noti-icon"></i>
                  <span className="badge bg-danger rounded-circle noti-icon-badge">5</span>
                </a>
                <div className="dropdown-menu dropdown-menu-end dropdown-lg">
                  {/* item*/}
                  <div className="dropdown-item noti-title">
                    <h5 className="m-0">
                      <span className="float-end">
                        <a href="" className="text-dark">
                          <small>Clear All</small>
                        </a>
                      </span>Notification
                    </h5>
                  </div>

                  <div className="noti-scroll" data-simplebar>
                    {/* item*/}
                    <a href="javascript:void(0);" className="dropdown-item notify-item active">
                      <div className="notify-icon bg-soft-primary text-primary">
                        <i className="mdi mdi-comment-account-outline"></i>
                      </div>
                      <p className="notify-details">Doug Dukes commented on Admin Dashboard
                        <small className="text-muted">1 min ago</small>
                      </p>
                    </a>
                    {/* item*/}
                    <a href="javascript:void(0);" className="dropdown-item notify-item">
                      <div className="notify-icon">
                        <img src="assets/images/users/avatar-2.jpg" className="img-fluid rounded-circle" alt="" />
                      </div>
                      <p className="notify-details">Mario Drummond</p>
                      <p className="text-muted mb-0 user-msg">
                        <small>Hi, How are you? What about our next meeting</small>
                      </p>
                    </a>
                    {/* item*/}
                    <a href="javascript:void(0);" className="dropdown-item notify-item">
                      <div className="notify-icon">
                        <img src="assets/images/users/avatar-4.jpg" className="img-fluid rounded-circle" alt="" />
                      </div>
                      <p className="notify-details">Karen Robinson</p>
                      <p className="text-muted mb-0 user-msg">
                        <small>Wow ! this admin looks good and awesome design</small>
                      </p>
                    </a>
                    {/* item*/}
                    <a href="javascript:void(0);" className="dropdown-item notify-item">
                      <div className="notify-icon bg-soft-warning text-warning">
                        <i className="mdi mdi-account-plus"></i>
                      </div>
                      <p className="notify-details">New user registered.
                        <small className="text-muted">5 hours ago</small>
                      </p>
                    </a>
                    {/* item*/}
                    <a href="javascript:void(0);" className="dropdown-item notify-item">
                      <div className="notify-icon bg-info">
                        <i className="mdi mdi-comment-account-outline"></i>
                      </div>
                      <p className="notify-details">Caleb Flakelar commented on Admin
                        <small className="text-muted">4 days ago</small>
                      </p>
                    </a>
                    {/* item*/}
                    <a href="javascript:void(0);" className="dropdown-item notify-item">
                      <div className="notify-icon bg-secondary">
                        <i className="mdi mdi-heart"></i>
                      </div>
                      <p className="notify-details">Carlos Crouch liked
                        <b>Admin</b>
                        <small className="text-muted">13 days ago</small>
                      </p>
                    </a>
                  </div>

                  {/* All*/}
                  <a href="javascript:void(0);" className="dropdown-item text-center text-primary notify-item notify-all">
                    View all
                    <i className="fe-arrow-right"></i>
                  </a>
                </div>
              </li>

              <li className="dropdown notification-list topbar-dropdown">
                <a className="nav-link dropdown-toggle nav-user me-0 waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  <img src="assets/images/users/avatar-1.jpg" alt="user-image" className="rounded-circle" />
                  <span className="pro-user-name ms-1">
                    {user?.username} <i className="mdi mdi-chevron-down"></i>
                  </span>
                </a>
                <div className="dropdown-menu dropdown-menu-end profile-dropdown ">
                  {/* item*/}
                  <div className="dropdown-header noti-title">
                    <h6 className="text-overflow m-0">Welcome !</h6>
                  </div>
                  {/* item*/}
                  <Link to="/profile" className="dropdown-item notify-item">
                    <i className="ri-account-circle-line"></i>
                    <span>My Account</span>
                  </Link>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item notify-item">
                    <i className="ri-settings-3-line"></i>
                    <span>Settings</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item notify-item">
                    <i className="ri-wallet-line"></i>
                    <span>My Wallet <span className="badge bg-success float-end">3</span> </span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item notify-item">
                    <i className="ri-lock-line"></i>
                    <span>Lock Screen</span>
                  </a>
                  <div className="dropdown-divider"></div>
                  {/* item*/}
                  <a href="#" className="dropdown-item notify-item" onClick={(e) => { e.preventDefault(); handleLogout(); }}>
                    <i className="ri-logout-box-line"></i>
                    <span>Logout</span>
                  </a>
                </div>
              </li>

              <li className="dropdown notification-list">
                <a className="nav-link waves-effect waves-light" data-bs-toggle="offcanvas" href="#theme-settings-offcanvas">
                  <i className="fe-settings noti-icon"></i>
                </a>
              </li>
            </ul>

            {/* LOGO */}
            <div className="logo-box">
              <a href="index.html" className="logo logo-dark text-center">
                <span className="logo-sm">
                  <img src="assets/images/logo-sm-dark.png" alt="" height="24" />
                </span>
                <span className="logo-lg">
                  <img src="assets/images/logo-dark.png" alt="" height="20" />
                </span>
              </a>

              <a href="index.html" className="logo logo-light text-center">
                <span className="logo-sm">
                  <img src="assets/images/logo-sm.png" alt="" height="24" />
                </span>
                <span className="logo-lg">
                  <img src="assets/images/logo-light.png" alt="" height="20" />
                </span>
              </a>
            </div>

            <ul className="list-unstyled topnav-menu topnav-menu-left m-0">
              <li>
                <button className="button-menu-mobile waves-effect waves-light">
                  <i className="fe-menu"></i>
                </button>
              </li>

              <li>
                {/* Mobile menu toggle (Horizontal Layout)*/}
                <a className="navbar-toggle nav-link" data-bs-toggle="collapse" data-bs-target="#topnav-menu-content">
                  <div className="lines">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </a>
                {/* End mobile menu toggle*/}
              </li>

              <li className="dropdown d-none d-xl-block">
                <a className="nav-link dropdown-toggle waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  Create New
                  <i className="mdi mdi-chevron-down"></i>
                </a>
                <div className="dropdown-menu">
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <i className="fe-briefcase me-1"></i>
                    <span>New Projects</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <i className="fe-user me-1"></i>
                    <span>Create Users</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <i className="fe-bar-chart-line- me-1"></i>
                    <span>Revenue Report</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <i className="fe-settings me-1"></i>
                    <span>Settings</span>
                  </a>
                  <div className="dropdown-divider"></div>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item">
                    <i className="fe-headphones me-1"></i>
                    <span>Help & Support</span>
                  </a>
                </div>
              </li>

              <li className="dropdown dropdown-mega d-none d-xl-block">
                <a className="nav-link dropdown-toggle waves-effect waves-light" data-bs-toggle="dropdown" href="#" role="button" aria-haspopup="false" aria-expanded="false">
                  Mega Menu
                  <i className="mdi mdi-chevron-down"></i>
                </a>
                <div className="dropdown-menu dropdown-megamenu">
                  <div className="row">
                    <div className="col-sm-8">
                      <div className="row">
                        <div className="col-md-4">
                          <h5 className="text-dark mt-0">UI Components</h5>
                          <ul className="list-unstyled megamenu-list">
                            <li>
                              <a href="javascript:void(0);">Widgets</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Nestable List</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Range Sliders</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Masonry Items</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Sweet Alerts</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Treeview Page</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Tour Page</a>
                            </li>
                          </ul>
                        </div>

                        <div className="col-md-4">
                          <h5 className="text-dark mt-0">Applications</h5>
                          <ul className="list-unstyled megamenu-list">
                            <li>
                              <a href="javascript:void(0);">eCommerce Pages</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">CRM Pages</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Email</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Calendar</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Team Contacts</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Task Board</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Email Templates</a>
                            </li>
                          </ul>
                        </div>

                        <div className="col-md-4">
                          <h5 className="text-dark mt-0">Extra Pages</h5>
                          <ul className="list-unstyled megamenu-list">
                            <li>
                              <a href="javascript:void(0);">Left Sidebar with User</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Menu Collapsed</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Small Left Sidebar</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">New Header Style</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Search Result</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Gallery Pages</a>
                            </li>
                            <li>
                              <a href="javascript:void(0);">Maintenance & Coming Soon</a>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                    <div className="col-sm-4">
                      <div className="text-center mt-3">
                        <h3 className="text-dark">Special Discount Sale!</h3>
                        <h4>Save up to 70% off.</h4>
                        <button className="btn btn-primary rounded-pill mt-3">Download Now</button>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
            <div className="clearfix"></div>
          </div>
        </div>
        {/* Topbar End */}

        {/* ========== Left Sidebar Start ========== */}
        <div className="left-side-menu">
          {/* LOGO */}
          <div className="logo-box">
            <a href="index.html" className="logo logo-dark text-center">
              <span className="logo-sm">
                <img src="assets/images/logo-sm-dark.png" alt="" height="24" />
              </span>
              <span className="logo-lg">
                <img src="assets/images/logo-dark.png" alt="" height="20" />
              </span>
            </a>

            <a href="index.html" className="logo logo-light text-center">
              <span className="logo-sm">
                <img src="assets/images/logo-sm.png" alt="" height="24" />
              </span>
              <span className="logo-lg">
                <img src="assets/images/logo-light.png" alt="" height="20" />
              </span>
            </a>
          </div>

          <div className="h-100" data-simplebar>
            {/* User box */}
            <div className="user-box text-center">
              <img src="assets/images/users/avatar-1.jpg" alt="user-img" title="Mat Helme" className="rounded-circle avatar-md" />
              <div className="dropdown">
                <a href="#" className="text-reset dropdown-toggle h5 mt-2 mb-1 d-block" data-bs-toggle="dropdown">{user?.username}</a>
                <div className="dropdown-menu user-pro-dropdown">
                  {/* item*/}
                  <Link to="/profile" className="dropdown-item notify-item">
                    <i className="fe-user me-1"></i>
                    <span>My Account</span>
                  </Link>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item notify-item">
                    <i className="fe-settings me-1"></i>
                    <span>Settings</span>
                  </a>
                  {/* item*/}
                  <a href="javascript:void(0);" className="dropdown-item notify-item">
                    <i className="fe-lock me-1"></i>
                    <span>Lock Screen</span>
                  </a>
                  {/* item*/}
                  <a href="#" className="dropdown-item notify-item" onClick={(e) => { e.preventDefault(); handleLogout(); }}>
                    <i className="fe-log-out me-1"></i>
                    <span>Logout</span>
                  </a>
                </div>
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
                      <Link to={item.href} className={isActive ? 'active' : ''}>
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
              {/* MAIN CONTENT AREA - Replace this comment with <Outlet /> */}
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
                  <script>document.write(new Date().getFullYear())</script> &copy; Minton theme by <a href="">Coderthemes</a>
                </div>
                <div className="col-md-6">
                  <div className="text-md-end footer-links d-none d-sm-block">
                    <a href="javascript:void(0);">About Us</a>
                    <a href="javascript:void(0);">Help</a>
                    <a href="javascript:void(0);">Contact Us</a>
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

      {/* Right Sidebar */}
      <div className="offcanvas offcanvas-end right-bar" tabIndex={-1} id="theme-settings-offcanvas" data-bs-scroll="true" data-bs-backdrop="true">
        <div data-simplebar className="h-100">
          {/* Nav tabs */}
          <ul className="nav nav-tabs nav-bordered nav-justified" role="tablist">
            <li className="nav-item">
              <a className="nav-link py-2" data-bs-toggle="tab" href="#chat-tab" role="tab">
                <i className="mdi mdi-message-text-outline d-block font-22 my-1"></i>
              </a>
            </li>
            <li className="nav-item">
              <a className="nav-link py-2" data-bs-toggle="tab" href="#tasks-tab" role="tab">
                <i className="mdi mdi-format-list-checkbox d-block font-22 my-1"></i>
              </a>
            </li>
            <li className="nav-item">
              <a className="nav-link py-2 active" data-bs-toggle="tab" href="#settings-tab" role="tab">
                <i className="mdi mdi-cog-outline d-block font-22 my-1"></i>
              </a>
            </li>
          </ul>

          {/* Tab panes */}
          <div className="tab-content pt-0">
            <div className="tab-pane" id="chat-tab" role="tabpanel">
              <form className="search-bar p-3">
                <div className="position-relative">
                  <input type="text" className="form-control" placeholder="Search..." />
                  <span className="mdi mdi-magnify"></span>
                </div>
              </form>

              <h6 className="fw-medium px-3 mt-2 text-uppercase">Group Chats</h6>

              <div className="p-2">
                <a href="javascript: void(0);" className="text-reset notification-item ps-3 mb-2 d-block">
                  <i className="mdi mdi-checkbox-blank-circle-outline me-1 text-success"></i>
                  <span className="mb-0 mt-1">App Development</span>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item ps-3 mb-2 d-block">
                  <i className="mdi mdi-checkbox-blank-circle-outline me-1 text-warning"></i>
                  <span className="mb-0 mt-1">Office Work</span>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item ps-3 mb-2 d-block">
                  <i className="mdi mdi-checkbox-blank-circle-outline me-1 text-danger"></i>
                  <span className="mb-0 mt-1">Personal Group</span>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item ps-3 d-block">
                  <i className="mdi mdi-checkbox-blank-circle-outline me-1"></i>
                  <span className="mb-0 mt-1">Freelance</span>
                </a>
              </div>

              <h6 className="fw-medium px-3 mt-3 text-uppercase">Favourites <a href="javascript: void(0);" className="font-18 text-danger"><i className="float-end mdi mdi-plus-circle"></i></a></h6>

              <div className="p-2">
                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status"></span>
                      <img src="assets/images/users/avatar-10.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Andrew Mackie</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">It will seem like simplified English.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status"></span>
                      <img src="assets/images/users/avatar-1.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Rory Dalyell</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">To an English person, it will seem like simplified</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status busy"></span>
                      <img src="assets/images/users/avatar-9.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Jaxon Dunhill</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">To achieve this, it would be necessary.</p>
                      </div>
                    </div>
                  </div>
                </a>
              </div>

              <h6 className="fw-medium px-3 mt-3 text-uppercase">Other Chats <a href="javascript: void(0);" className="font-18 text-danger"><i className="float-end mdi mdi-plus-circle"></i></a></h6>

              <div className="p-2 pb-4">
                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status online"></span>
                      <img src="assets/images/users/avatar-2.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Jackson Therry</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">Everyone realizes why a new common language.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status away"></span>
                      <img src="assets/images/users/avatar-4.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Charles Deakin</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">The languages only differ in their grammar.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status online"></span>
                      <img src="assets/images/users/avatar-5.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Ryan Salting</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">If several languages coalesce the grammar of the resulting.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status online"></span>
                      <img src="assets/images/users/avatar-6.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Sean Howse</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">It will seem like simplified English.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status busy"></span>
                      <img src="assets/images/users/avatar-7.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Dean Coward</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">The new common language will be more simple.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset notification-item">
                  <div className="d-flex align-items-start">
                    <div className="position-relative me-2">
                      <span className="user-status away"></span>
                      <img src="assets/images/users/avatar-8.jpg" className="rounded-circle avatar-sm" alt="user-pic" />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <h6 className="mt-0 mb-1 font-14">Hayley East</h6>
                      <div className="font-13 text-muted">
                        <p className="mb-0 text-truncate">One could refuse to pay expensive translators.</p>
                      </div>
                    </div>
                  </div>
                </a>

                <div className="text-center mt-3">
                  <a href="javascript:void(0);" className="btn btn-sm btn-white">
                    <i className="mdi mdi-spin mdi-loading me-2"></i>
                    Load more
                  </a>
                </div>
              </div>
            </div>

            <div className="tab-pane" id="tasks-tab" role="tabpanel">
              <h6 className="fw-medium p-3 m-0 text-uppercase">Working Tasks</h6>
              <div className="px-2">
                <a href="javascript: void(0);" className="text-reset item-hovered d-block p-2">
                  <p className="text-muted mb-0">App Development<span className="float-end">75%</span></p>
                  <div className="progress mt-2" style={{ height: '4px' }}>
                    <div className="progress-bar bg-success" role="progressbar" style={{ width: '75%' }} aria-valuenow={75} aria-valuemin={0} aria-valuemax={100}></div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset item-hovered d-block p-2">
                  <p className="text-muted mb-0">Database Repair<span className="float-end">37%</span></p>
                  <div className="progress mt-2" style={{ height: '4px' }}>
                    <div className="progress-bar bg-info" role="progressbar" style={{ width: '37%' }} aria-valuenow={37} aria-valuemin={0} aria-valuemax={100}></div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset item-hovered d-block p-2">
                  <p className="text-muted mb-0">Backup Create<span className="float-end">52%</span></p>
                  <div className="progress mt-2" style={{ height: '4px' }}>
                    <div className="progress-bar bg-warning" role="progressbar" style={{ width: '52%' }} aria-valuenow={52} aria-valuemin={0} aria-valuemax={100}></div>
                  </div>
                </a>
              </div>

              <h6 className="fw-medium px-3 mb-0 mt-4 text-uppercase">Upcoming Tasks</h6>

              <div className="p-2">
                <a href="javascript: void(0);" className="text-reset item-hovered d-block p-2">
                  <p className="text-muted mb-0">Sales Reporting<span className="float-end">12%</span></p>
                  <div className="progress mt-2" style={{ height: '4px' }}>
                    <div className="progress-bar bg-danger" role="progressbar" style={{ width: '12%' }} aria-valuenow={12} aria-valuemin={0} aria-valuemax={100}></div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset item-hovered d-block p-2">
                  <p className="text-muted mb-0">Redesign Website<span className="float-end">67%</span></p>
                  <div className="progress mt-2" style={{ height: '4px' }}>
                    <div className="progress-bar bg-primary" role="progressbar" style={{ width: '67%' }} aria-valuenow={67} aria-valuemin={0} aria-valuemax={100}></div>
                  </div>
                </a>

                <a href="javascript: void(0);" className="text-reset item-hovered d-block p-2">
                  <p className="text-muted mb-0">New Admin Design<span className="float-end">84%</span></p>
                  <div className="progress mt-2" style={{ height: '4px' }}>
                    <div className="progress-bar bg-success" role="progressbar" style={{ width: '84%' }} aria-valuenow={84} aria-valuemin={0} aria-valuemax={100}></div>
                  </div>
                </a>
              </div>

              <div className="d-grid p-3 mt-2">
                <a href="javascript: void(0);" className="btn btn-success waves-effect waves-light">Create Task</a>
              </div>
            </div>

            <div className="tab-pane active" id="settings-tab" role="tabpanel">
              <h6 className="fw-medium px-3 m-0 py-2 font-13 text-uppercase bg-light">
                <span className="d-block py-1">Theme Settings</span>
              </h6>

              <div className="p-3">
                <div className="alert alert-warning" role="alert">
                  <strong>Customize </strong> the overall color scheme, sidebar menu, etc.
                </div>

                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Color Scheme</h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-bs-theme" value="light" id="light-mode-check" defaultChecked />
                  <label className="form-check-label" htmlFor="light-mode-check">Light Mode</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-bs-theme" value="dark" id="dark-mode-check" />
                  <label className="form-check-label" htmlFor="dark-mode-check">Dark Mode</label>
                </div>

                {/* Width */}
                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Width</h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-layout-width" value="fluid" id="fluid-check" defaultChecked />
                  <label className="form-check-label" htmlFor="fluid-check">Fluid</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-layout-width" value="boxed" id="boxed-check" />
                  <label className="form-check-label" htmlFor="boxed-check">Boxed</label>
                </div>

                {/* Topbar */}
                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Topbar</h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-topbar-color" value="light" id="lighttopbar-check" />
                  <label className="form-check-label" htmlFor="lighttopbar-check">Light</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-topbar-color" value="dark" id="darktopbar-check" defaultChecked />
                  <label className="form-check-label" htmlFor="darktopbar-check">Dark</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-topbar-color" value="brand" id="brandtopbar-check" />
                  <label className="form-check-label" htmlFor="brandtopbar-check">brand</label>
                </div>

                {/* Menu positions */}
                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Menus Positon <small>(Leftsidebar and Topbar)</small></h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-layout-position" value="fixed" id="fixed-check" defaultChecked />
                  <label className="form-check-label" htmlFor="fixed-check">Fixed</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-layout-position" value="scrollable" id="scrollable-check" />
                  <label className="form-check-label" htmlFor="scrollable-check">Scrollable</label>
                </div>

                {/* Menu Color*/}
                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Menu Color</h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-menu-color" value="light" id="light-check" defaultChecked />
                  <label className="form-check-label" htmlFor="light-check">Light</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-menu-color" value="dark" id="dark-check" />
                  <label className="form-check-label" htmlFor="dark-check">Dark</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-menu-color" value="brand" id="brand-check" />
                  <label className="form-check-label" htmlFor="brand-check">Brand</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-menu-color" value="gradient" id="gradient-check" />
                  <label className="form-check-label" htmlFor="gradient-check">Gradient</label>
                </div>

                {/* size */}
                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Left Sidebar Size</h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-sidebar-size" value="default" id="default-size-check" defaultChecked />
                  <label className="form-check-label" htmlFor="default-size-check">Default</label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-sidebar-size" value="condensed" id="condensed-check" />
                  <label className="form-check-label" htmlFor="condensed-check">Condensed <small>(Extra Small size)</small></label>
                </div>

                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-sidebar-size" value="compact" id="compact-check" />
                  <label className="form-check-label" htmlFor="compact-check">Compact <small>(Small size)</small></label>
                </div>

                {/* User info */}
                <h6 className="fw-medium font-14 mt-4 mb-2 pb-1">Sidebar User Info</h6>
                <div className="form-check form-switch mb-1">
                  <input className="form-check-input" type="checkbox" name="data-sidebar-user" value="true" id="sidebaruser-check" />
                  <label className="form-check-label" htmlFor="sidebaruser-check">Enable</label>
                </div>

                <div className="d-grid mt-4">
                  <button className="btn btn-primary" id="resetBtn">Reset to Default</button>

                  <a href="#" className="btn btn-danger mt-2" target="_blank"><i className="mdi mdi-basket me-1"></i> Purchase Now</a>
                </div>
              </div>
            </div>
          </div>
        </div> {/* end slimscroll-menu*/}
      </div>
      {/* /Right-bar */}

      {/* Right bar overlay*/}
      <div className="rightbar-overlay"></div>
    </>
  );
};

export default LayoutFull;