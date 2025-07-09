import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuthStore } from '@/store/authStore'

interface LogMessage {
  type: 'log' | 'error' | 'connected' | 'disconnected'
  data?: string
  message?: string
  service_id?: string
  timestamp?: string
}

interface UseServiceLogsOptions {
  hostId: string
  serviceId: string
  tail?: number
  follow?: boolean
  timestamps?: boolean
  autoConnect?: boolean
}

export const useServiceLogs = ({
  hostId,
  serviceId,
  tail = 100,
  follow = true,
  timestamps = false,
  autoConnect = true
}: UseServiceLogsOptions) => {
  const [logs, setLogs] = useState<LogMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const ws = useRef<WebSocket | null>(null)
  const { token } = useAuthStore()
  
  const connect = useCallback(() => {
    if (!hostId || !serviceId || !token) return
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }
    
    setIsConnecting(true)
    setError(null)
    
    // Build WebSocket URL
    const wsUrl = new URL(`/api/v1/services/${serviceId}/logs`, window.location.origin)
    wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl.searchParams.set('host_id', hostId)
    wsUrl.searchParams.set('tail', tail.toString())
    wsUrl.searchParams.set('follow', follow.toString())
    wsUrl.searchParams.set('timestamps', timestamps.toString())
    wsUrl.searchParams.set('token', token)
    
    const websocket = new WebSocket(wsUrl.toString())
    
    websocket.onopen = () => {
      setIsConnected(true)
      setIsConnecting(false)
      setError(null)
      
      // Add connection message
      setLogs(prev => [...prev, {
        type: 'connected',
        message: `Connected to service ${serviceId}`,
        timestamp: new Date().toISOString()
      }])
    }
    
    websocket.onmessage = (event) => {
      try {
        const message: LogMessage = JSON.parse(event.data)
        setLogs(prev => [...prev, message])
      } catch (err) {
        // Handle raw text messages
        setLogs(prev => [...prev, {
          type: 'log',
          data: event.data,
          timestamp: new Date().toISOString()
        }])
      }
    }
    
    websocket.onclose = (event) => {
      setIsConnected(false)
      setIsConnecting(false)
      
      if (event.code !== 1000) {
        const errorMsg = `Connection closed: ${event.reason || 'Unknown reason'}`
        setError(errorMsg)
        setLogs(prev => [...prev, {
          type: 'disconnected',
          message: errorMsg,
          timestamp: new Date().toISOString()
        }])
      }
    }
    
    websocket.onerror = (event) => {
      setIsConnected(false)
      setIsConnecting(false)
      setError('WebSocket connection error')
      
      setLogs(prev => [...prev, {
        type: 'error',
        message: 'WebSocket connection error',
        timestamp: new Date().toISOString()
      }])
    }
    
    ws.current = websocket
  }, [hostId, serviceId, token, tail, follow, timestamps])
  
  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close(1000, 'User disconnected')
      ws.current = null
    }
  }, [])
  
  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])
  
  const reconnect = useCallback(() => {
    disconnect()
    setTimeout(connect, 1000)
  }, [disconnect, connect])
  
  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    
    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])
  
  return {
    logs,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    reconnect,
    clearLogs
  }
}