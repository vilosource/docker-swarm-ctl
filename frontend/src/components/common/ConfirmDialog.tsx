import { useEffect, useRef } from 'react'

interface ConfirmDialogProps {
  show: boolean
  onHide: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmVariant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info'
}

export default function ConfirmDialog({
  show,
  onHide,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'danger'
}: ConfirmDialogProps) {
  const backdropRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    if (show) {
      document.body.classList.add('modal-open')
    } else {
      document.body.classList.remove('modal-open')
    }
    
    return () => {
      document.body.classList.remove('modal-open')
    }
  }, [show])
  
  const handleConfirm = () => {
    onConfirm()
    onHide()
  }
  
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) {
      onHide()
    }
  }

  if (!show) return null

  return (
    <>
      <div 
        className="modal fade show d-block" 
        tabIndex={-1}
        style={{ display: 'block' }}
      >
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">{title}</h5>
              <button 
                type="button" 
                className="btn-close" 
                onClick={onHide}
                aria-label="Close"
              />
            </div>
            <div className="modal-body">
              {message}
            </div>
            <div className="modal-footer">
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={onHide}
              >
                {cancelText}
              </button>
              <button 
                type="button" 
                className={`btn btn-${confirmVariant}`} 
                onClick={handleConfirm}
              >
                {confirmText}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div 
        ref={backdropRef}
        className="modal-backdrop fade show" 
        onClick={handleBackdropClick}
      />
    </>
  )
}