import { useUnifiedLogStream, LogEntry } from './useUnifiedLogStream'

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
  const {
    logs: unifiedLogs,
    isConnected,
    isConnecting,
    error,
    clearLogs,
    reconnect,
    disconnect
  } = useUnifiedLogStream({
    sourceType: 'service',
    resourceId: serviceId,
    hostId,
    tail,
    follow,
    timestamps,
    enabled: autoConnect
  })

  // Transform unified logs to match the existing interface
  // This maintains backward compatibility with existing components
  const logs = unifiedLogs.map(log => ({
    type: log.type as 'log' | 'error' | 'connected' | 'disconnected',
    data: log.data,
    message: log.message,
    service_id: log.source_id,
    timestamp: log.timestamp
  }))

  return {
    logs,
    isConnected,
    isConnecting,
    error: error?.message || null,
    connect: reconnect,
    disconnect,
    reconnect,
    clearLogs
  }
}