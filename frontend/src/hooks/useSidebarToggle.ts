import { useState, useEffect } from 'react'

export function useSidebarToggle() {
  const [isCondensed, setIsCondensed] = useState(false)
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Initialize from localStorage
  useEffect(() => {
    const savedState = localStorage.getItem('sidebar-condensed')
    if (savedState === 'true') {
      setIsCondensed(true)
      document.documentElement.setAttribute('data-sidebar-size', 'condensed')
    }
  }, [])

  const toggleSidebar = () => {
    const isMobile = window.innerWidth < 768
    
    if (isMobile) {
      // On mobile, toggle the sidebar visibility
      setIsMobileOpen(!isMobileOpen)
      document.documentElement.classList.toggle('sidebar-enable')
      
      // Show backdrop on mobile
      if (!isMobileOpen) {
        showBackdrop()
      } else {
        hideBackdrop()
      }
    } else {
      // On desktop, toggle between condensed and full
      const newCondensed = !isCondensed
      setIsCondensed(newCondensed)
      
      if (newCondensed) {
        document.documentElement.setAttribute('data-sidebar-size', 'condensed')
        localStorage.setItem('sidebar-condensed', 'true')
      } else {
        document.documentElement.removeAttribute('data-sidebar-size')
        localStorage.removeItem('sidebar-condensed')
      }
    }
  }

  const showBackdrop = () => {
    const backdrop = document.createElement('div')
    backdrop.id = 'custom-backdrop'
    backdrop.className = 'offcanvas-backdrop fade show'
    document.body.appendChild(backdrop)
    document.body.style.overflow = 'hidden'

    backdrop.addEventListener('click', () => {
      document.documentElement.classList.remove('sidebar-enable')
      hideBackdrop()
      setIsMobileOpen(false)
    })
  }

  const hideBackdrop = () => {
    const backdrop = document.getElementById('custom-backdrop')
    if (backdrop) {
      backdrop.remove()
      document.body.style.overflow = ''
    }
  }

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        // Remove mobile classes when resizing to desktop
        document.documentElement.classList.remove('sidebar-enable')
        hideBackdrop()
        setIsMobileOpen(false)
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return {
    isCondensed,
    isMobileOpen,
    toggleSidebar
  }
}