import { useState, useCallback, useRef, useEffect } from 'react'
import { useWebSocket } from './useWebSocket'
import { useAuthStore } from '@/store/authStore'

interface ContainerStats {
  timestamp: string
  cpu_percent: number
  memory: {
    usage: number
    limit: number
    percent: number
  }
  networks: Record<string, {
    rx_bytes: number
    tx_bytes: number
  }>
  block_io: {
    read_bytes: number
    write_bytes: number
  }
}

interface UseContainerStatsOptions {
  maxDataPoints?: number
  enabled?: boolean
}

interface StatsData {
  timestamps: string[]
  cpu: number[]
  memory: number[]
  networkRx: number[]
  networkTx: number[]
  blockRead: number[]
  blockWrite: number[]
}

export function useContainerStats(
  containerId: string,
  options: UseContainerStatsOptions = {}
) {
  const { maxDataPoints = 60, enabled = true } = options
  const { token } = useAuthStore()
  
  const [stats, setStats] = useState<StatsData>({
    timestamps: [],
    cpu: [],
    memory: [],
    networkRx: [],
    networkTx: [],
    blockRead: [],
    blockWrite: []
  })
  
  const [currentStats, setCurrentStats] = useState<ContainerStats | null>(null)
  const [error, setError] = useState<Error | null>(null)
  
  // Keep track of previous network/block values for calculating rates
  const previousStats = useRef<{
    networkRx: number
    networkTx: number
    blockRead: number
    blockWrite: number
  } | null>(null)
  
  const handleMessage = useCallback((message: any) => {
    if (message.type === 'stats' && message.data) {
      const newStats: ContainerStats = {
        timestamp: message.timestamp,
        cpu_percent: message.data.cpu_percent,
        memory: message.data.memory,
        networks: message.data.networks || {},
        block_io: message.data.block_io || { read_bytes: 0, write_bytes: 0 }
      }
      
      setCurrentStats(newStats)
      
      // Calculate network totals
      let totalRx = 0
      let totalTx = 0
      Object.values(newStats.networks).forEach(net => {
        totalRx += net.rx_bytes || 0
        totalTx += net.tx_bytes || 0
      })
      
      // Calculate rates (bytes per second)
      let rxRate = 0
      let txRate = 0
      let readRate = 0
      let writeRate = 0
      
      if (previousStats.current) {
        rxRate = Math.max(0, totalRx - previousStats.current.networkRx)
        txRate = Math.max(0, totalTx - previousStats.current.networkTx)
        readRate = Math.max(0, (newStats.block_io.read_bytes || 0) - previousStats.current.blockRead)
        writeRate = Math.max(0, (newStats.block_io.write_bytes || 0) - previousStats.current.blockWrite)
      }
      
      previousStats.current = {
        networkRx: totalRx,
        networkTx: totalTx,
        blockRead: newStats.block_io.read_bytes || 0,
        blockWrite: newStats.block_io.write_bytes || 0
      }
      
      // Update chart data
      setStats(prev => {
        const newData = {
          timestamps: [...prev.timestamps, new Date(newStats.timestamp).toLocaleTimeString()],
          cpu: [...prev.cpu, newStats.cpu_percent],
          memory: [...prev.memory, newStats.memory.percent],
          networkRx: [...prev.networkRx, rxRate],
          networkTx: [...prev.networkTx, txRate],
          blockRead: [...prev.blockRead, readRate],
          blockWrite: [...prev.blockWrite, writeRate]
        }
        
        // Keep only the last maxDataPoints
        if (newData.timestamps.length > maxDataPoints) {
          Object.keys(newData).forEach(key => {
            newData[key as keyof StatsData] = newData[key as keyof StatsData].slice(-maxDataPoints)
          })
        }
        
        return newData
      })
    } else if (message.type === 'error') {
      setError(new Error(message.message))
    }
  }, [maxDataPoints])
  
  const handleError = useCallback((error: Event) => {
    console.error('Stats WebSocket error:', error)
    setError(new Error('WebSocket connection error'))
  }, [])
  
  const wsUrl = enabled && containerId && token
    ? `${import.meta.env.VITE_WS_URL || 'ws://localhost/ws'}/containers/${containerId}/stats?token=${token}`
    : null
  
  const { isConnected, isConnecting, error: wsError, reconnect } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    onError: handleError,
    autoReconnect: true,
    reconnectDelay: 5000,
    enabled: enabled && !!containerId && !!token
  })
  
  // Clear stats when container changes
  useEffect(() => {
    setStats({
      timestamps: [],
      cpu: [],
      memory: [],
      networkRx: [],
      networkTx: [],
      blockRead: [],
      blockWrite: []
    })
    setCurrentStats(null)
    previousStats.current = null
  }, [containerId])
  
  const clearStats = useCallback(() => {
    setStats({
      timestamps: [],
      cpu: [],
      memory: [],
      networkRx: [],
      networkTx: [],
      blockRead: [],
      blockWrite: []
    })
  }, [])
  
  return {
    stats,
    currentStats,
    isConnected,
    isConnecting,
    error: error || wsError,
    reconnect,
    clearStats
  }
}