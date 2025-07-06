/**
 * Format bytes to human-readable string
 */
export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

/**
 * Format date to human-readable string
 */
export function formatDate(date: string | Date): string {
  const d = new Date(date)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
  
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  
  // For older dates, show the actual date
  return d.toLocaleDateString()
}

/**
 * Format duration in seconds to human-readable string
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }
  
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  
  if (hours < 24) {
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
  }
  
  const days = Math.floor(hours / 24)
  const remainingHours = hours % 24
  
  return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`
}

/**
 * Truncate hostname for display
 * If the hostname is a FQDN, extract the short hostname
 * e.g., "docker-1.lab.viloforge.com" -> "docker-1.lab"
 */
export function truncateHostname(hostname: string, maxLength = 20): string {
  if (!hostname) return ''
  
  // If hostname is already short enough, return as is
  if (hostname.length <= maxLength) return hostname
  
  // Check if it's a FQDN (contains dots)
  const parts = hostname.split('.')
  if (parts.length > 2) {
    // For FQDN, try to return hostname + first domain part
    const shortName = `${parts[0]}.${parts[1]}`
    if (shortName.length <= maxLength) {
      return shortName
    }
    // If still too long, just return the hostname part
    return parts[0]
  }
  
  // For non-FQDN or if hostname is still too long, truncate with ellipsis
  if (hostname.length > maxLength) {
    return hostname.substring(0, maxLength - 3) + '...'
  }
  
  return hostname
}