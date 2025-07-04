import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts'
import { useContainerStats } from '../hooks/useContainerStats'

interface ContainerStatsProps {
  containerId: string
}

// Helper function to format bytes
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

// Helper function to format bytes per second
const formatBytesPerSec = (bytes: number): string => {
  return `${formatBytes(bytes)}/s`
}

export const ContainerStats: React.FC<ContainerStatsProps> = ({ containerId }) => {
  const { stats, currentStats, isConnected, isConnecting, error, reconnect } = useContainerStats(containerId)
  
  // Prepare data for charts
  const chartData = stats.timestamps.map((timestamp, index) => ({
    time: timestamp,
    cpu: stats.cpu[index],
    memory: stats.memory[index],
    networkRx: stats.networkRx[index],
    networkTx: stats.networkTx[index],
    blockRead: stats.blockRead[index],
    blockWrite: stats.blockWrite[index]
  }))
  
  if (!isConnected && !isConnecting) {
    return (
      <div className="alert alert-warning">
        <i className="mdi mdi-alert-circle me-2"></i>
        Not connected to stats stream
        <button className="btn btn-sm btn-warning ms-2" onClick={reconnect}>
          Reconnect
        </button>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="alert alert-danger">
        <i className="mdi mdi-alert-circle me-2"></i>
        Error: {error.message}
      </div>
    )
  }
  
  if (isConnecting) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Connecting to stats...</span>
        </div>
      </div>
    )
  }
  
  return (
    <div className="container-stats">
      {/* Current Stats Summary */}
      {currentStats && (
        <div className="row mb-4">
          <div className="col-md-3">
            <div className="card h-100">
              <div className="card-body d-flex flex-column">
                <h5 className="card-title">
                  <i className="mdi mdi-cpu-64-bit text-primary me-2"></i>
                  CPU Usage
                </h5>
                <div className="mt-auto">
                  <h2 className="mb-0">{currentStats.cpu_percent.toFixed(2)}%</h2>
                  <div style={{ height: '1.5rem' }}></div>
                </div>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card h-100">
              <div className="card-body d-flex flex-column">
                <h5 className="card-title">
                  <i className="mdi mdi-memory text-info me-2"></i>
                  Memory Usage
                </h5>
                <div className="mt-auto">
                  <h2 className="mb-0">{currentStats.memory.percent.toFixed(2)}%</h2>
                  <small className="text-muted d-block" style={{ height: '1.5rem' }}>
                    {formatBytes(currentStats.memory.usage)} / {formatBytes(currentStats.memory.limit)}
                  </small>
                </div>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card h-100">
              <div className="card-body d-flex flex-column">
                <h5 className="card-title">
                  <i className="mdi mdi-arrow-down-bold text-success me-2"></i>
                  Network RX
                </h5>
                <div className="mt-auto">
                  <h2 className="mb-0">
                    {formatBytesPerSec(stats.networkRx[stats.networkRx.length - 1] || 0)}
                  </h2>
                  <div style={{ height: '1.5rem' }}></div>
                </div>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card h-100">
              <div className="card-body d-flex flex-column">
                <h5 className="card-title">
                  <i className="mdi mdi-arrow-up-bold text-warning me-2"></i>
                  Network TX
                </h5>
                <div className="mt-auto">
                  <h2 className="mb-0">
                    {formatBytesPerSec(stats.networkTx[stats.networkTx.length - 1] || 0)}
                  </h2>
                  <div style={{ height: '1.5rem' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* CPU and Memory Chart */}
      <div className="card mb-4">
        <div className="card-body">
          <h5 className="card-title">CPU & Memory Usage</h5>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value: number) => `${value.toFixed(2)}%`}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="cpu" 
                stroke="#0d6efd" 
                strokeWidth={2}
                name="CPU %"
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="memory" 
                stroke="#6610f2" 
                strokeWidth={2}
                name="Memory %"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Network I/O Chart */}
      <div className="card mb-4">
        <div className="card-body">
          <h5 className="card-title">Network I/O</h5>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis tickFormatter={(value) => formatBytes(value)} />
              <Tooltip 
                formatter={(value: number) => formatBytesPerSec(value)}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="networkRx" 
                stackId="1"
                stroke="#198754" 
                fill="#198754"
                fillOpacity={0.6}
                name="RX (bytes/s)"
              />
              <Area 
                type="monotone" 
                dataKey="networkTx" 
                stackId="1"
                stroke="#ffc107" 
                fill="#ffc107"
                fillOpacity={0.6}
                name="TX (bytes/s)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Block I/O Chart */}
      <div className="card">
        <div className="card-body">
          <h5 className="card-title">Block I/O</h5>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis tickFormatter={(value) => formatBytes(value)} />
              <Tooltip 
                formatter={(value: number) => formatBytesPerSec(value)}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="blockRead" 
                stackId="1"
                stroke="#0dcaf0" 
                fill="#0dcaf0"
                fillOpacity={0.6}
                name="Read (bytes/s)"
              />
              <Area 
                type="monotone" 
                dataKey="blockWrite" 
                stackId="1"
                stroke="#dc3545" 
                fill="#dc3545"
                fillOpacity={0.6}
                name="Write (bytes/s)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}