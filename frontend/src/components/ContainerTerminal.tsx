import React, { useEffect, useRef, useState } from 'react'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { WebLinksAddon } from 'xterm-addon-web-links'
import { useAuthStore } from '@/store/authStore'
import 'xterm/css/xterm.css'

interface ContainerTerminalProps {
  containerId: string
  command?: string
  workdir?: string
  hostId?: string
}

export const ContainerTerminal: React.FC<ContainerTerminalProps> = ({ 
  containerId, 
  command,
  workdir = '/',
  hostId
}) => {
  const terminalRef = useRef<HTMLDivElement>(null)
  const terminalInstanceRef = useRef<Terminal | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actualCommand, setActualCommand] = useState<string>(command || 'auto-detect')
  const { token } = useAuthStore()

  useEffect(() => {
    if (!terminalRef.current || !token) return

    // Small delay to ensure DOM is ready
    const initTimeout = setTimeout(() => {
      if (!terminalRef.current) return

      // Create terminal instance
      const term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'Consolas, "Courier New", monospace',
        theme: {
          background: '#1e1e1e',
          foreground: '#d4d4d4',
          cursor: '#d4d4d4',
          black: '#000000',
          red: '#cd3131',
          green: '#0dbc79',
          yellow: '#e5e510',
          blue: '#2472c8',
          magenta: '#bc3fbc',
          cyan: '#11a8cd',
          white: '#e5e5e5',
          brightBlack: '#666666',
          brightRed: '#f14c4c',
          brightGreen: '#23d18b',
          brightYellow: '#f5f543',
          brightBlue: '#3b8eea',
          brightMagenta: '#d670d6',
          brightCyan: '#29b8db',
          brightWhite: '#e5e5e5'
        }
      })

      // Add addons
      const fit = new FitAddon()
      const webLinks = new WebLinksAddon()
      term.loadAddon(fit)
      term.loadAddon(webLinks)

      // Open terminal in DOM
      term.open(terminalRef.current)
      
      // Fit after a small delay to ensure dimensions are available
      setTimeout(() => {
        fit.fit()
      }, 100)

      terminalInstanceRef.current = term
      fitAddonRef.current = fit

      // Connect WebSocket
      let wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost/ws'}/containers/${containerId}/exec?token=${token}`
      if (command) {
        wsUrl += `&cmd=${encodeURIComponent(command)}`
      }
      wsUrl += `&workdir=${encodeURIComponent(workdir)}`
      if (hostId) {
        wsUrl += `&host_id=${hostId}`
      }
      const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
      term.writeln('\r\n\x1b[32mConnecting to container...\x1b[0m\r\n')
    }

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        // Binary data - terminal output
        event.data.arrayBuffer().then(buffer => {
          const decoder = new TextDecoder()
          const text = decoder.decode(buffer)
          term.write(text)
        })
      } else {
        // Text data - control messages
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'connected') {
            term.writeln(`\x1b[32m${message.message}\x1b[0m\r\n`)
            // Extract shell info if provided
            if (message.shell) {
              setActualCommand(message.shell)
            }
          } else if (message.type === 'error') {
            term.writeln(`\x1b[31mError: ${message.message}\x1b[0m\r\n`)
            setError(message.message)
          }
        } catch (e) {
          // Not JSON, treat as text
          term.write(event.data)
        }
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setError('Connection error')
      term.writeln('\r\n\x1b[31mConnection error\x1b[0m\r\n')
    }

    ws.onclose = () => {
      setIsConnected(false)
      term.writeln('\r\n\x1b[33mConnection closed\x1b[0m\r\n')
    }

      socketRef.current = ws

      // Handle terminal input
      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          // Send as binary to preserve special characters
          ws.send(new TextEncoder().encode(data))
        }
      })

      // Handle resize
      const handleResize = () => {
        if (fit) {
          fit.fit()
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'resize',
              rows: term.rows,
              cols: term.cols
            }))
          }
        }
      }

      // Store resize handler for cleanup
      (window as any)._terminalResizeHandler = handleResize

      // Add resize listener
      window.addEventListener('resize', handleResize)
      
      // Initial resize after a short delay
      setTimeout(handleResize, 100)
    }, 50)

    // Cleanup
    return () => {
      clearTimeout(initTimeout)
      const handler = (window as any)._terminalResizeHandler
      if (handler) {
        window.removeEventListener('resize', handler)
      }
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close()
      }
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.dispose()
      }
    }
  }, [containerId, command, workdir, token])

  const reconnect = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.close()
    }
    // Clean up terminal
    if (terminalInstanceRef.current) {
      terminalInstanceRef.current.dispose()
      terminalInstanceRef.current = null
    }
    socketRef.current = null
    fitAddonRef.current = null
    setError(null)
    // Small delay before reconnecting
    setTimeout(() => {
      // Clear the terminal div
      if (terminalRef.current) {
        terminalRef.current.innerHTML = ''
      }
      // Force re-render
      setIsConnected(false)
    }, 100)
  }

  return (
    <div className="container-terminal h-100 d-flex flex-column">
      {/* Terminal toolbar */}
      <div className="terminal-toolbar border-bottom p-2">
        <div className="row align-items-center">
          <div className="col-auto">
            <span className={`badge ${isConnected ? 'bg-success' : 'bg-danger'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="col">
            <small className="text-muted">
              Shell: {actualCommand} | Working Dir: {workdir}
            </small>
          </div>
          <div className="col-auto">
            {!isConnected && (
              <button 
                className="btn btn-sm btn-outline-primary"
                onClick={reconnect}
              >
                <i className="mdi mdi-refresh me-1"></i>
                Reconnect
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Terminal container */}
      <div className="flex-grow-1 bg-dark p-2" style={{ minHeight: '400px' }}>
        <div ref={terminalRef} className="h-100" />
      </div>

      {/* Error display */}
      {error && (
        <div className="alert alert-danger m-2" role="alert">
          <i className="mdi mdi-alert-circle me-2"></i>
          {error}
        </div>
      )}
    </div>
  )
}