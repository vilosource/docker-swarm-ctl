import { useState, useEffect, useRef } from 'react'
import { useServiceLogs } from '@/hooks/useServiceLogs'
import { formatDistanceToNow } from 'date-fns'

interface ServiceLogViewerProps {
  hostId: string
  serviceId: string
  serviceName?: string
  className?: string
}

export default function ServiceLogViewer({ 
  hostId, 
  serviceId, 
  serviceName,
  className = ''
}: ServiceLogViewerProps) {
  const [autoScroll, setAutoScroll] = useState(true)
  const [showTimestamps, setShowTimestamps] = useState(false)
  const [tail, setTail] = useState(100)
  const [filter, setFilter] = useState('')
  const [logLevel, setLogLevel] = useState<'all' | 'error' | 'warn' | 'info'>('all')
  
  const logContainerRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  
  const { 
    logs, 
    isConnected, 
    isConnecting, 
    error, 
    connect, 
    disconnect, 
    reconnect, 
    clearLogs 
  } = useServiceLogs({
    hostId,
    serviceId,
    tail,
    follow: true,
    timestamps: showTimestamps,
    autoConnect: true
  })
  
  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, autoScroll])
  
  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10
      setAutoScroll(isAtBottom)
    }
  }
  
  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      setAutoScroll(true)
    }
  }
  
  const getLogLevel = (logData: string): 'error' | 'warn' | 'info' | 'debug' => {
    const lowerData = logData.toLowerCase()
    if (lowerData.includes('error') || lowerData.includes('err') || lowerData.includes('exception')) {
      return 'error'
    } else if (lowerData.includes('warn') || lowerData.includes('warning')) {
      return 'warn'
    } else if (lowerData.includes('info')) {
      return 'info'
    }
    return 'debug'
  }
  
  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'text-red-400'
      case 'warn': return 'text-yellow-400'
      case 'info': return 'text-blue-400'
      case 'debug': return 'text-gray-400'
      default: return 'text-gray-300'
    }
  }
  
  const filteredLogs = logs.filter(log => {
    if (!log.data) return true // Show system messages
    
    // Filter by text
    if (filter && !log.data.toLowerCase().includes(filter.toLowerCase())) {
      return false
    }
    
    // Filter by log level
    if (logLevel !== 'all') {
      const level = getLogLevel(log.data)
      if (level !== logLevel) {
        return false
      }
    }
    
    return true
  })
  
  const copyToClipboard = () => {
    const logText = logs
      .filter(log => log.data)
      .map(log => log.data)
      .join('\n')
    
    navigator.clipboard.writeText(logText).then(() => {
      // Could add toast notification here
      console.log('Logs copied to clipboard')
    })
  }
  
  const downloadLogs = () => {
    const logText = logs
      .filter(log => log.data)
      .map(log => {
        const timestamp = log.timestamp ? new Date(log.timestamp).toISOString() : ''
        return `${timestamp} ${log.data}`
      })
      .join('\n')
    
    const blob = new Blob([logText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${serviceName || serviceId}-logs.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header Controls */}
      <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 
              isConnecting ? 'bg-yellow-500' : 
              'bg-red-500'
            }`} />
            <span className="text-sm text-gray-300">
              {isConnected ? 'Connected' : 
               isConnecting ? 'Connecting...' : 
               'Disconnected'}
            </span>
          </div>
          
          <div className="text-sm text-gray-400">
            Service: <span className="text-gray-200">{serviceName || serviceId}</span>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Log Level Filter */}
          <select 
            value={logLevel}
            onChange={(e) => setLogLevel(e.target.value as any)}
            className="px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-300"
          >
            <option value="all">All Levels</option>
            <option value="error">Errors</option>
            <option value="warn">Warnings</option>
            <option value="info">Info</option>
          </select>
          
          {/* Text Filter */}
          <input
            type="text"
            placeholder="Filter logs..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-300 placeholder-gray-500"
          />
          
          {/* Tail Lines */}
          <select 
            value={tail}
            onChange={(e) => setTail(Number(e.target.value))}
            className="px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-300"
            disabled={isConnected}
          >
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={500}>500 lines</option>
            <option value={1000}>1000 lines</option>
          </select>
          
          {/* Timestamps Toggle */}
          <label className="flex items-center space-x-1 text-xs text-gray-400">
            <input
              type="checkbox"
              checked={showTimestamps}
              onChange={(e) => setShowTimestamps(e.target.checked)}
              className="w-3 h-3"
            />
            <span>Timestamps</span>
          </label>
        </div>
      </div>
      
      {/* Action Bar */}
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <button
            onClick={reconnect}
            disabled={isConnecting}
            className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-white"
          >
            {isConnecting ? 'Connecting...' : 'Reconnect'}
          </button>
          
          <button
            onClick={clearLogs}
            className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 rounded text-white"
          >
            Clear
          </button>
          
          <button
            onClick={copyToClipboard}
            className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 rounded text-white"
          >
            Copy
          </button>
          
          <button
            onClick={downloadLogs}
            className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 rounded text-white"
          >
            Download
          </button>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">
            {filteredLogs.length} / {logs.length} lines
          </span>
          
          {!autoScroll && (
            <button
              onClick={scrollToBottom}
              className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded text-white"
            >
              ↓ Follow
            </button>
          )}
        </div>
      </div>
      
      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900 border-b border-red-700 text-red-200 text-sm">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={reconnect}
              className="ml-2 px-2 py-1 text-xs bg-red-700 hover:bg-red-600 rounded"
            >
              Retry
            </button>
          </div>
        </div>
      )}
      
      {/* Log Container */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-auto bg-black text-gray-100 font-mono text-sm"
        onScroll={handleScroll}
      >
        <div ref={logContainerRef} className="p-2">
          {filteredLogs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              {isConnecting ? 'Connecting to service logs...' : 'No logs to display'}
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div key={index} className="flex items-start py-0.5 hover:bg-gray-800">
                {/* Timestamp */}
                {showTimestamps && log.timestamp && (
                  <span className="text-gray-500 text-xs mr-2 flex-shrink-0 w-20">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                )}
                
                {/* Log Content */}
                <div className="flex-1 min-w-0">
                  {log.type === 'log' && log.data ? (
                    <span className={getLogLevelColor(getLogLevel(log.data))}>
                      {log.data}
                    </span>
                  ) : log.type === 'error' ? (
                    <span className="text-red-400">
                      ERROR: {log.message}
                    </span>
                  ) : log.type === 'connected' ? (
                    <span className="text-green-400">
                      ✓ {log.message}
                    </span>
                  ) : log.type === 'disconnected' ? (
                    <span className="text-yellow-400">
                      ⚠ {log.message}
                    </span>
                  ) : (
                    <span className="text-gray-400">
                      {log.message}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Footer */}
      <div className="p-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
        <div className="flex items-center justify-between">
          <span>
            Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
          </span>
          <span>
            Last updated: {logs.length > 0 && logs[logs.length - 1]?.timestamp 
              ? formatDistanceToNow(new Date(logs[logs.length - 1].timestamp), { addSuffix: true })
              : 'Never'}
          </span>
        </div>
      </div>
    </div>
  )
}