import { useMemo } from 'react'
import { useUnifiedLogStream } from './useUnifiedLogStream'

export interface UseContainerLogsOptions {
  follow?: boolean
  tail?: number
  timestamps?: boolean
  since?: string
  hostId?: string
}

export function useContainerLogs(
  containerId: string | null,
  options: UseContainerLogsOptions = {}
) {
  const {
    follow = true,
    tail = 100,
    timestamps = true,
    since,
    hostId
  } = options

  const {
    logs: unifiedLogs,
    isConnected,
    isConnecting,
    error,
    clearLogs,
    reconnect,
    scrollToBottom,
    logsEndRef
  } = useUnifiedLogStream({
    sourceType: 'container',
    resourceId: containerId,
    hostId,
    tail,
    follow,
    timestamps,
    enabled: !!containerId
  })

  // Extract just the log data strings for backward compatibility
  const logs = useMemo(() => {
    return unifiedLogs
      .filter(log => log.type === 'log' && log.data)
      .map(log => log.data!)
  }, [unifiedLogs])

  // Determine if we're actively streaming (have received logs)
  const isStreaming = isConnected && logs.length > 0

  return {
    logs,
    isConnected,
    isStreaming,
    error,
    clearLogs,
    reconnect,
    scrollToBottom,
    logsEndRef
  }
}