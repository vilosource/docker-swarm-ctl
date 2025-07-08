import React, { useEffect, useState } from 'react'
import { useToast } from '@/contexts/ToastContext'

export default function ToastContainer() {
  const { toasts, removeToast } = useToast()

  return (
    <div 
      className="toast-container position-fixed bottom-0 end-0 p-3"
      style={{ zIndex: 1050 }}
    >
      {toasts.map(toast => (
        <Toast 
          key={toast.id}
          toast={toast}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  )
}

interface ToastProps {
  toast: {
    id: string
    message: string
    type: 'success' | 'error' | 'warning' | 'info'
    duration?: number
  }
  onClose: () => void
}

function Toast({ toast, onClose }: ToastProps) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    // Trigger animation
    setTimeout(() => setShow(true), 10)
  }, [])

  const handleClose = () => {
    setShow(false)
    setTimeout(onClose, 300) // Wait for fade out animation
  }

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return 'mdi-check-circle'
      case 'error':
        return 'mdi-alert-circle'
      case 'warning':
        return 'mdi-alert'
      case 'info':
      default:
        return 'mdi-information'
    }
  }

  const getColorClass = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-success'
      case 'error':
        return 'bg-danger'
      case 'warning':
        return 'bg-warning'
      case 'info':
      default:
        return 'bg-info'
    }
  }

  return (
    <div 
      className={`toast align-items-center text-white ${getColorClass()} border-0 ${show ? 'show' : ''}`}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      style={{ minWidth: '300px' }}
    >
      <div className="d-flex">
        <div className="toast-body d-flex align-items-center">
          <i className={`mdi ${getIcon()} me-2`} style={{ fontSize: '1.2rem' }}></i>
          <span>{toast.message}</span>
        </div>
        <button 
          type="button" 
          className="btn-close btn-close-white me-2 m-auto" 
          aria-label="Close"
          onClick={handleClose}
        ></button>
      </div>
    </div>
  )
}