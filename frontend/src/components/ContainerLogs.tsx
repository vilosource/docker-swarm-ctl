import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useContainerLogs } from '../hooks/useContainerLogs'

interface ContainerLogsProps {
  containerId: string
}

export const ContainerLogs: React.FC<ContainerLogsProps> = ({ containerId }) => {
  const [follow, setFollow] = useState(true)
  const [displayTail, setDisplayTail] = useState(100)
  const [initialTail] = useState(100) // Only used for initial connection
  const [searchTerm, setSearchTerm] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const logsContainerRef = useRef<HTMLDivElement>(null)

  const {
    logs,
    isConnected,
    isStreaming,
    error,
    clearLogs,
    reconnect,
    logsEndRef,
  } = useContainerLogs(containerId, { follow, tail: initialTail })

  // Filter logs based on search term and display tail
  const filteredLogs = useMemo(() => {
    let filtered = logs
    
    // Apply tail filter
    if (displayTail > 0 && filtered.length > displayTail) {
      filtered = filtered.slice(-displayTail)
    }
    
    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(log => 
        log.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }
    
    return filtered
  }, [logs, searchTerm, displayTail])

  // Handle log download
  const handleDownload = useCallback(() => {
    const content = logs.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `container-${containerId}-logs.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [logs, containerId])

  // Parse log line to extract timestamp and message
  const parseLogLine = (line: string) => {
    // Docker logs format: 2024-01-01T12:00:00.000000000Z message
    const timestampMatch = line.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+(.*)$/)
    if (timestampMatch) {
      return {
        timestamp: new Date(timestampMatch[1]).toLocaleTimeString(),
        message: timestampMatch[2],
      }
    }
    return { timestamp: null, message: line }
  }

  // Auto-scroll effect
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [filteredLogs, autoScroll])

  return (
    <div className="h-100 d-flex flex-column">
      {/* Toolbar */}
      <div className="border-bottom p-2">
        <div className="row align-items-center">
          <div className="col-auto">
            <span className={`badge ${isConnected ? 'bg-success' : 'bg-danger'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            {isStreaming && (
              <span className="badge bg-info ms-2">Streaming</span>
            )}
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
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={displayTail}
              onChange={(e) => setDisplayTail(Number(e.target.value))}
            >
              <option value={50}>Last 50 lines</option>
              <option value={100}>Last 100 lines</option>
              <option value={200}>Last 200 lines</option>
              <option value={500}>Last 500 lines</option>
              <option value={1000}>Last 1000 lines</option>
            </select>
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

          <div className="col-auto">
            <div className="form-check form-check-inline">
              <input
                className="form-check-input"
                type="checkbox"
                id="follow"
                checked={follow}
                onChange={(e) => setFollow(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="follow">
                Follow
              </label>
            </div>
          </div>

          <div className="col-auto">
            <div className="btn-group btn-group-sm" role="group">
              <button
                className="btn btn-outline-secondary"
                onClick={() => setFollow(!follow)}
                disabled={!isConnected}
                title={isStreaming ? 'Pause' : 'Resume'}
              >
                <i className={`mdi ${isStreaming ? 'mdi-pause' : 'mdi-play'}`}></i>
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={clearLogs}
                title="Clear logs"
              >
                <i className="mdi mdi-notification-clear-all"></i>
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={reconnect}
                disabled={isConnected}
                title="Reconnect"
              >
                <i className="mdi mdi-refresh"></i>
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={handleDownload}
                disabled={logs.length === 0}
                title="Download logs"
              >
                <i className="mdi mdi-download"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="alert alert-danger m-2" role="alert">
          <i className="mdi mdi-alert-circle me-2"></i>
          {error.message || error.toString()}
        </div>
      )}

      {/* Logs display */}
      <div
        ref={logsContainerRef}
        className="flex-grow-1 overflow-auto bg-dark text-light font-monospace p-3"
        style={{
          fontSize: '0.875rem',
          lineHeight: '1.5',
          minHeight: '200px'
        }}
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
            {searchTerm ? 'No logs match your search' : 'No logs available'}
          </div>
        )}

        {filteredLogs.map((log, index) => {
          const { timestamp, message } = parseLogLine(log)
          return (
            <div key={index} className="log-line d-flex" style={{ minHeight: '1.5rem' }}>
              <span className="text-muted pe-3" style={{ minWidth: '50px', userSelect: 'none' }}>
                {index + 1}
              </span>
              {timestamp && (
                <span className="text-info pe-3" style={{ minWidth: '100px' }}>
                  {timestamp}
                </span>
              )}
              <span className="flex-grow-1" style={{ wordBreak: 'break-all' }}>
                {message}
              </span>
            </div>
          )
        })}

        {/* Scroll anchor */}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}