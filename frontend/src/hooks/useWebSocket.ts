import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'

interface UseWebSocketOptions {
  onOpen?: () => void
  onMessage?: (data: any) => void
  onError?: (error: Event) => void
  onClose?: (event: CloseEvent) => void
  autoReconnect?: boolean
  reconnectDelay?: number
  reconnectAttempts?: number
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {}
) {
  const [state, setState] = useState<{
    connected: boolean
    connecting: boolean
    error: Error | null
  }>({
    connected: false,
    connecting: false,
    error: null
  })

  const ws = useRef<WebSocket | null>(null)
  const reconnectCount = useRef(0)
  const reconnectTimeout = useRef<NodeJS.Timeout>()

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return
    
    setState(s => ({ ...s, connecting: true, error: null }))
    
    const token = useAuthStore.getState().token
    const wsUrl = `${url}?token=${token}`
    
    ws.current = new WebSocket(wsUrl)
    
    ws.current.onopen = () => {
      setState({ connected: true, connecting: false, error: null })
      reconnectCount.current = 0
      options.onOpen?.()
    }
    
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Handle errors
        if (data.type === 'error') {
          if (data.fatal) {
            ws.current?.close()
          }
          setState(s => ({ ...s, error: new Error(data.message) }))
          return
        }
        
        options.onMessage?.(data)
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }
    
    ws.current.onerror = (error) => {
      setState(s => ({ ...s, error: new Error('WebSocket error') }))
      options.onError?.(error)
    }
    
    ws.current.onclose = (event) => {
      setState({ connected: false, connecting: false, error: null })
      options.onClose?.(event)
      
      // Auto-reconnect logic
      if (
        options.autoReconnect &&
        reconnectCount.current < (options.reconnectAttempts || 5)
      ) {
        reconnectCount.current++
        const delay = Math.min(
          1000 * Math.pow(2, reconnectCount.current),
          options.reconnectDelay || 30000
        )
        reconnectTimeout.current = setTimeout(connect, delay)
      }
    }
  }, [url, options])

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeout.current)
    ws.current?.close()
    ws.current = null
  }, [])

  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  return { ...state, send, reconnect: connect, disconnect }
}