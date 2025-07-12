import { useEffect, useState, useRef, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'
import { useAuthStore } from '../store/authStore'

export type LogSourceType = 'container' | 'service' | 'host' | 'daemon' | 'stack'

export interface LogEntry {
  type: 'log' | 'error' | 'connected' | 'disconnected' | 'complete' | 'heartbeat'
  timestamp: string
  source_type?: LogSourceType
  source_id?: string
  message?: string
  data?: string
  level?: string
  metadata?: Record<string, any>
}

export interface UseUnifiedLogStreamOptions {
  sourceType: LogSourceType
  resourceId: string | null
  hostId?: string
  tail?: number
  follow?: boolean
  timestamps?: boolean
  enabled?: boolean
  autoScroll?: boolean
}

export interface UseUnifiedLogStreamReturn {
  logs: LogEntry[]
  isConnected: boolean
  isConnecting: boolean
  error: Error | null
  clearLogs: () => void
  reconnect: () => void
  disconnect: () => void
  scrollToBottom: () => void
  logsEndRef: React.RefObject<HTMLDivElement>
}

export function useUnifiedLogStream({
  sourceType,
  resourceId,
  hostId,
  tail = 100,
  follow = true,
  timestamps = true,
  enabled = true,
  autoScroll = true
}: UseUnifiedLogStreamOptions): UseUnifiedLogStreamReturn {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const { token } = useAuthStore()

  // Build WebSocket URL based on source type
  const wsUrl = resourceId && token && enabled
    ? buildLogWebSocketUrl(sourceType, resourceId, {
        host_id: hostId,
        tail,
        follow,
        timestamps,
        token
      })
    : null

  // Handle incoming messages
  const handleMessage = useCallback((message: LogEntry) => {
    // Handle different message types
    switch (message.type) {
      case 'log':
        // Add log entry
        setLogs(prev => [...prev, message])
        break
      
      case 'connected':
        // Add connection message
        setLogs(prev => [...prev, {
          ...message,
          data: message.message || `Connected to ${sourceType} logs`
        }])
        break
      
      case 'disconnected':
        // Add disconnection message
        setLogs(prev => [...prev, {
          ...message,
          data: message.message || 'Disconnected from log stream'
        }])
        break
      
      case 'error':
        // Add error message
        console.error('Log stream error:', message.message)
        setLogs(prev => [...prev, {
          ...message,
          data: `Error: ${message.message}`
        }])
        break
      
      case 'complete':
        // Add completion message
        setLogs(prev => [...prev, {
          ...message,
          data: message.message || 'Log stream completed'
        }])
        break
      
      case 'heartbeat':
        // Ignore heartbeats - they just keep the connection alive
        break
      
      default:
        // Unknown message type
        console.warn('Unknown log message type:', message.type)
    }
  }, [sourceType])

  // Use the WebSocket hook
  const {
    isConnected,
    isConnecting,
    error,
    reconnect,
    disconnect
  } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    enabled: !!wsUrl
  })

  // Clear logs when resource changes
  useEffect(() => {
    setLogs([])
  }, [resourceId, sourceType])

  // Auto-scroll to bottom when new logs arrive
  const scrollToBottom = useCallback(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [])

  useEffect(() => {
    if (autoScroll && logs.length > 0) {
      scrollToBottom()
    }
  }, [logs, autoScroll, scrollToBottom])

  // Clear logs function
  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  return {
    logs,
    isConnected,
    isConnecting,
    error,
    clearLogs,
    reconnect,
    disconnect,
    scrollToBottom,
    logsEndRef
  }
}

// Helper function to build WebSocket URL based on source type
function buildLogWebSocketUrl(
  sourceType: LogSourceType,
  resourceId: string,
  params: Record<string, any>
): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  
  // Service logs use a different path structure
  if (sourceType === 'service') {
    // Don't use VITE_WS_URL for service logs, construct directly
    const baseUrl = `${wsProtocol}//${host}`
    const endpoint = `/api/v1/services/${resourceId}/logs`
    
    // Build query string
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value))
      }
    })
    
    return `${baseUrl}${endpoint}?${queryParams.toString()}`
  }
  
  // Other log types use the /ws prefix
  const baseUrl = import.meta.env.VITE_WS_URL || `${wsProtocol}//${host}/ws`
  
  // Map source types to endpoints
  const endpoints: Record<LogSourceType, string> = {
    container: `/containers/${resourceId}/logs`,
    service: `/services/${resourceId}/logs`, // This won't be used due to the check above
    host: `/hosts/${resourceId}/logs`,
    daemon: `/daemon/${resourceId}/logs`,
    stack: `/stacks/${resourceId}/logs`
  }
  
  const endpoint = endpoints[sourceType]
  if (!endpoint) {
    throw new Error(`Unknown log source type: ${sourceType}`)
  }
  
  // Build query string
  const queryParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      queryParams.append(key, String(value))
    }
  })
  
  return `${baseUrl}${endpoint}?${queryParams.toString()}`
}