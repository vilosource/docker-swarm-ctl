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
  
  // Reconnect when tail or timestamps change
  const previousTailRef = useRef(tail)
  const previousTimestampsRef = useRef(showTimestamps)
  useEffect(() => {
    if ((previousTailRef.current !== tail || previousTimestampsRef.current !== showTimestamps) && isConnected) {
      reconnect()
    }
    previousTailRef.current = tail
    previousTimestampsRef.current = showTimestamps
  }, [tail, showTimestamps, isConnected, reconnect])
  
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
    if (lowerData.includes('error') || lowerData.includes('err:') || lowerData.includes('exception') || lowerData.includes('failed')) {
      return 'error'
    } else if (lowerData.includes('warn') || lowerData.includes('warning')) {
      return 'warn'
    } else if (lowerData.includes('info:') || lowerData.includes('[info]')) {
      return 'info'
    }
    return 'debug'
  }
  
  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'text-danger'
      case 'warn': return 'text-warning'
      case 'info': return 'text-info'
      case 'debug': return 'text-secondary'
      default: return 'text-light'
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
      // For 'info' filter, show both 'info' and 'debug' logs
      if (logLevel === 'info' && (level === 'info' || level === 'debug')) {
        return true
      }
      // For other filters, match exactly
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
    <div className={`h-100 d-flex flex-column ${className}`}>
      {/* Header Controls */}
      <div className="border-bottom p-2">
        <div className="row align-items-center">
          <div className="col-auto">
            <span className={`badge ${
              isConnected ? 'bg-success' : 
              isConnecting ? 'bg-warning' : 
              'bg-danger'
            }`}>
              {isConnected ? 'Connected' : 
               isConnecting ? 'Connecting...' : 
               'Disconnected'}
            </span>
            <span className="text-muted ms-3">
              Service: <strong>{serviceName || serviceId}</strong>
            </span>
          </div>
          
          <div className="col">
            <div className="input-group input-group-sm">
              <span className="input-group-text">
                <i className="mdi mdi-magnify"></i>
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Search logs..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </div>
          </div>
          
          <div className="col-auto">
            <select 
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value as any)}
              className="form-select form-select-sm"
            >
              <option value="all">All Levels</option>
              <option value="error">Errors</option>
              <option value="warn">Warnings</option>
              <option value="info">Info</option>
            </select>
          </div>
          
          <div className="col-auto">
            <select 
              value={tail}
              onChange={(e) => setTail(Number(e.target.value))}
              className="form-select form-select-sm"
            >
              <option value={50}>Last 50 lines</option>
              <option value={100}>Last 100 lines</option>
              <option value={500}>Last 500 lines</option>
              <option value={1000}>Last 1000 lines</option>
            </select>
          </div>
          
          <div className="col-auto">
            <div className="form-check form-check-inline">
              <input
                className="form-check-input"
                type="checkbox"
                id="showTimestamps"
                checked={showTimestamps}
                onChange={(e) => setShowTimestamps(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="showTimestamps">
                Timestamps
              </label>
            </div>
          </div>
          
          <div className="col-auto">
            <div className="form-check form-check-inline">
              <input
                className="form-check-input"
                type="checkbox"
                id="autoScroll"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="autoScroll">
                Auto-scroll
              </label>
            </div>
          </div>
        </div>
      </div>
      
      {/* Action Bar */}
      <div className="border-bottom p-2">
        <div className="row align-items-center">
          <div className="col-auto">
            <div className="btn-group btn-group-sm">
              <button
                onClick={reconnect}
                disabled={isConnecting}
                className="btn btn-outline-primary"
                title="Reconnect"
              >
                <i className="mdi mdi-refresh"></i>
              </button>
              
              <button
                onClick={clearLogs}
                className="btn btn-outline-secondary"
                title="Clear logs"
              >
                <i className="mdi mdi-notification-clear-all"></i>
              </button>
              
              <button
                onClick={copyToClipboard}
                className="btn btn-outline-secondary"
                title="Copy logs"
              >
                <i className="mdi mdi-content-copy"></i>
              </button>
              
              <button
                onClick={downloadLogs}
                className="btn btn-outline-secondary"
                title="Download logs"
                disabled={logs.length === 0}
              >
                <i className="mdi mdi-download"></i>
              </button>
            </div>
          </div>
          
          <div className="col text-end">
            <span className="text-muted small">
              {filteredLogs.length} / {logs.length} lines
            </span>
            
            {!autoScroll && (
              <button
                onClick={scrollToBottom}
                className="btn btn-sm btn-primary ms-2"
              >
                <i className="mdi mdi-arrow-down"></i> Follow
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Error Display */}
      {error && (
        <div className="alert alert-danger m-2" role="alert">
          <i className="mdi mdi-alert-circle me-2"></i>
          {error}
          <button
            onClick={reconnect}
            className="btn btn-sm btn-danger float-end"
          >
            Retry
          </button>
        </div>
      )}
      
      {/* Log Container */}
      <div 
        ref={scrollRef}
        className="flex-grow-1 overflow-auto bg-dark text-light font-monospace p-3"
        style={{
          fontSize: '0.875rem',
          lineHeight: '1.5',
          minHeight: '200px'
        }}
        onScroll={handleScroll}
      >
        {!isConnected && !error && (
          <div className="text-center py-5">
            <div className="spinner-border text-light" role="status">
              <span className="visually-hidden">Connecting...</span>
            </div>
          </div>
        )}
        
        {isConnected && filteredLogs.length === 0 && (
          <div className="text-muted text-center py-5">
            {filter ? 'No logs match your search' : 'No logs available'}
          </div>
        )}
        
        {filteredLogs.map((log, index) => {
          const level = log.data ? getLogLevel(log.data) : 'info'
          const levelColorClass = getLogLevelColor(level)
          
          return (
            <div key={index} className="log-line d-flex" style={{ minHeight: '1.5rem' }}>
              <span className="text-muted pe-3" style={{ minWidth: '50px', userSelect: 'none' }}>
                {index + 1}
              </span>
              {showTimestamps && log.timestamp && (
                <span className="text-info pe-3" style={{ minWidth: '100px' }}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              )}
              <span className="flex-grow-1" style={{ wordBreak: 'break-all' }}>
                {log.type === 'log' && log.data ? (
                  <span className={levelColorClass}>
                    {log.data}
                  </span>
                ) : log.type === 'error' ? (
                  <span className="text-danger">
                    ERROR: {log.message}
                  </span>
                ) : log.type === 'connected' ? (
                  <span className="text-success">
                    ✓ {log.message}
                  </span>
                ) : log.type === 'disconnected' ? (
                  <span className="text-warning">
                    ⚠ {log.message}
                  </span>
                ) : (
                  <span className="text-muted">
                    {log.message}
                  </span>
                )}
              </span>
            </div>
          )
        })}
        
        {/* Scroll anchor */}
        <div ref={logContainerRef} />
      </div>
    </div>
  )
}