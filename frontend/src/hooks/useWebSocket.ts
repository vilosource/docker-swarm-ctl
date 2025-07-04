import { useEffect, useRef, useState, useCallback } from 'react'

interface UseWebSocketParams {
  url: string | null
  onMessage?: (data: any) => void
  onOpen?: () => void
  onError?: (error: Event) => void
  onClose?: (event: CloseEvent) => void
  autoReconnect?: boolean
  reconnectDelay?: number
  reconnectAttempts?: number
  enabled?: boolean
}

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onError,
  onClose,
  autoReconnect = true,
  reconnectDelay = 5000,
  reconnectAttempts = 5,
  enabled = true
}: UseWebSocketParams) {
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
  const isUnmounting = useRef(false)

  const connect = useCallback(() => {
    if (!url || !enabled) return
    
    // Check if we already have a connection or are connecting
    if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
      return
    }
    
    setState(s => ({ ...s, connecting: true, error: null }))
    
    // URL already includes token as query parameter from the calling component
    ws.current = new WebSocket(url)
    
    ws.current.onopen = () => {
      setState({ connected: true, connecting: false, error: null })
      reconnectCount.current = 0
      onOpen?.()
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
        
        onMessage?.(data)
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }
    
    ws.current.onerror = (error) => {
      setState(s => ({ ...s, error: new Error('WebSocket error') }))
      onError?.(error)
    }
    
    ws.current.onclose = (event) => {
      console.log(`WebSocket closed: Code ${event.code}, Reason: ${event.reason || 'No reason provided'}`)
      
      // Create a more descriptive error message
      let errorMessage = 'WebSocket connection closed'
      if (event.reason) {
        errorMessage = event.reason
      } else if (event.code === 1008) {
        errorMessage = 'Authentication failed - invalid or expired token'
      } else if (event.code === 1006) {
        errorMessage = 'Connection lost - network error'
      }
      
      setState({ connected: false, connecting: false, error: new Error(errorMessage) })
      onClose?.(event)
      
      // Auto-reconnect logic
      if (
        autoReconnect &&
        reconnectCount.current < reconnectAttempts &&
        event.code !== 1008 && // Don't reconnect on auth failure
        !isUnmounting.current // Don't reconnect if component is unmounting
      ) {
        reconnectCount.current++
        const delay = Math.min(
          1000 * Math.pow(2, reconnectCount.current),
          reconnectDelay
        )
        console.log(`Reconnecting in ${delay}ms...`)
        reconnectTimeout.current = setTimeout(connect, delay)
      }
    }
  }, [url, enabled, onMessage, onOpen, onError, onClose, autoReconnect, reconnectAttempts, reconnectDelay])

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimeout.current)
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      ws.current.close(1000, 'Normal closure')
    }
    ws.current = null
  }, [])

  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    isUnmounting.current = false
    let connectionTimeout: NodeJS.Timeout
    
    if (enabled && url) {
      // Small delay to avoid React StrictMode double-render issues
      connectionTimeout = setTimeout(() => {
        if (!isUnmounting.current) {
          connect()
        }
      }, 100)
    }
    
    return () => {
      isUnmounting.current = true
      clearTimeout(connectionTimeout)
      disconnect()
    }
  }, [connect, disconnect, enabled, url])

  return { 
    isConnected: state.connected,
    isConnecting: state.connecting,
    error: state.error,
    send, 
    reconnect: connect, 
    disconnect 
  }
}