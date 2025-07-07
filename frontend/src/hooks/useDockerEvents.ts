import { useEffect, useRef, useCallback, useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useHostStore } from '@/store/hostStore'

export interface DockerEvent {
  Type: string
  Action: string
  Actor: {
    ID: string
    Attributes: Record<string, string>
  }
  time: number
  timeNano: number
  host_id: string
}

export interface EventMessage {
  type: 'connected' | 'event' | 'error' | 'pong'
  timestamp: string
  host_id?: string
  event?: DockerEvent
  error?: string
  filters?: string
}

interface UseDockerEventsOptions {
  hostId?: string
  filters?: {
    type?: string[]
    action?: string[]
    label?: Record<string, string>
    container?: string[]
    image?: string[]
  }
  onEvent?: (event: DockerEvent) => void
  maxEvents?: number
}

export function useDockerEvents({
  hostId = 'all',
  filters,
  onEvent,
  maxEvents = 100
}: UseDockerEventsOptions = {}) {
  const token = useAuthStore((state) => state.token)
  const [events, setEvents] = useState<DockerEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const pingIntervalRef = useRef<NodeJS.Timeout>()

  const connect = useCallback(() => {
    if (!token || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsUrl = new URL('/ws/events', window.location.origin)
      wsUrl.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      wsUrl.searchParams.set('token', token)
      wsUrl.searchParams.set('host_id', hostId)
      
      if (filters) {
        wsUrl.searchParams.set('filters', JSON.stringify(filters))
      }

      const ws = new WebSocket(wsUrl.toString())
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Connected to Docker events stream')
        setIsConnected(true)
        setError(null)
        
        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000) // Ping every 30 seconds
      }

      ws.onmessage = (event) => {
        try {
          const message: EventMessage = JSON.parse(event.data)
          
          switch (message.type) {
            case 'connected':
              console.log('Events stream connected:', message)
              break
              
            case 'event':
              if (message.event) {
                setEvents((prev) => {
                  const newEvents = [message.event!, ...prev]
                  // Limit the number of stored events
                  return newEvents.slice(0, maxEvents)
                })
                
                if (onEvent) {
                  onEvent(message.event)
                }
              }
              break
              
            case 'error':
              console.error('Event stream error:', message.error)
              setError(message.error || 'Unknown error')
              break
              
            case 'pong':
              // Pong received, connection is alive
              break
          }
        } catch (err) {
          console.error('Failed to parse event message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setError('Connection error')
      }

      ws.onclose = () => {
        console.log('Disconnected from Docker events stream')
        setIsConnected(false)
        wsRef.current = null
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
        }
        
        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect to events stream...')
          connect()
        }, 5000)
      }
    } catch (err) {
      console.error('Failed to connect to events stream:', err)
      setError('Failed to connect')
    }
  }, [token, hostId, filters, onEvent, maxEvents])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
    }
    
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    
    setIsConnected(false)
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    events,
    isConnected,
    error,
    clearEvents
  }
}