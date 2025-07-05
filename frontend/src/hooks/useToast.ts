export function useToast() {
  const showToast = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    // For now, use console. In production, integrate with a toast library
    console.log(`[${type.toUpperCase()}] ${message}`)
    
    // You can integrate with bootstrap toasts or a library like react-toastify
    // Example with bootstrap:
    // const toastEl = document.createElement('div')
    // toastEl.className = `toast align-items-center text-white bg-${type} border-0`
    // toastEl.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div></div>`
    // document.body.appendChild(toastEl)
    // const toast = new bootstrap.Toast(toastEl)
    // toast.show()
  }
  
  return { showToast }
}