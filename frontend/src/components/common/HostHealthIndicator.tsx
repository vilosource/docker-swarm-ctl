import { FC } from 'react'

interface HostHealthIndicatorProps {
  status: 'pending' | 'healthy' | 'unhealthy' | 'unreachable'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  lastHealthCheck?: string
}

export const HostHealthIndicator: FC<HostHealthIndicatorProps> = ({
  status,
  size = 'md',
  showLabel = false,
  lastHealthCheck
}) => {
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  }

  const statusConfig = {
    pending: {
      color: 'bg-gray-400',
      label: 'Pending',
      icon: 'mdi mdi-timer-sand'
    },
    healthy: {
      color: 'bg-success',
      label: 'Healthy',
      icon: 'mdi mdi-check-circle'
    },
    unhealthy: {
      color: 'bg-warning',
      label: 'Unhealthy',
      icon: 'mdi mdi-alert-circle'
    },
    unreachable: {
      color: 'bg-danger',
      label: 'Unreachable',
      icon: 'mdi mdi-close-circle'
    }
  }

  const config = statusConfig[status]
  
  const getTooltip = () => {
    if (!lastHealthCheck) return config.label
    const date = new Date(lastHealthCheck)
    return `${config.label} - Last checked: ${date.toLocaleString()}`
  }

  return (
    <div className="d-inline-flex align-items-center" title={getTooltip()}>
      <div className={`rounded-circle ${config.color} ${sizeClasses[size]}`}></div>
      {showLabel && (
        <span className={`ms-2 text-${status === 'healthy' ? 'success' : status === 'unreachable' ? 'danger' : 'warning'}`}>
          {config.label}
        </span>
      )}
    </div>
  )
}