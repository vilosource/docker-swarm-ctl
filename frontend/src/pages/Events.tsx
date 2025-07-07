import { useState } from 'react'
import { useDockerEvents } from '@/hooks/useDockerEvents'
import PageTitle from '@/components/common/PageTitle'
import { useHostStore } from '@/store/hostStore'
import { formatDistanceToNow } from 'date-fns'

const EVENT_TYPE_COLORS: Record<string, string> = {
  container: 'text-blue-600',
  image: 'text-green-600',
  network: 'text-purple-600',
  volume: 'text-orange-600',
  node: 'text-red-600',
  service: 'text-indigo-600',
  secret: 'text-pink-600',
  config: 'text-yellow-600'
}

const EVENT_ACTION_ICONS: Record<string, string> = {
  create: '➕',
  start: '▶️',
  stop: '⏹️',
  pause: '⏸️',
  unpause: '▶️',
  restart: '🔄',
  kill: '☠️',
  die: '💀',
  destroy: '🗑️',
  remove: '🗑️',
  delete: '🗑️',
  attach: '🔗',
  detach: '🔓',
  pull: '⬇️',
  push: '⬆️',
  tag: '🏷️',
  untag: '🏷️',
  import: '📥',
  export: '📤',
  load: '📥',
  save: '💾',
  connect: '🔌',
  disconnect: '🔌',
  mount: '📎',
  unmount: '📎'
}

export default function Events() {
  const selectedHostId = useHostStore((state) => state.selectedHostId)
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  
  const { events, isConnected, error, clearEvents } = useDockerEvents({
    hostId: selectedHostId || 'all',
    filters: typeFilter !== 'all' ? { type: [typeFilter] } : undefined
  })

  const filteredEvents = events.filter((event) => {
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase()
      const actorName = event.Actor.Attributes.name || ''
      const actorId = event.Actor.ID || ''
      const image = event.Actor.Attributes.image || ''
      
      return (
        actorName.toLowerCase().includes(searchLower) ||
        actorId.toLowerCase().includes(searchLower) ||
        image.toLowerCase().includes(searchLower) ||
        event.Type.toLowerCase().includes(searchLower) ||
        event.Action.toLowerCase().includes(searchLower)
      )
    }
    return true
  })

  const getEventDescription = (event: typeof events[0]) => {
    const { Type, Action, Actor } = event
    const name = Actor.Attributes.name || Actor.ID.substring(0, 12)
    
    switch (Type) {
      case 'container':
        return `Container ${name} ${Action}`
      case 'image':
        return `Image ${name} ${Action}`
      case 'network':
        return `Network ${name} ${Action}`
      case 'volume':
        return `Volume ${name} ${Action}`
      case 'node':
        return `Node ${name} ${Action}`
      case 'service':
        return `Service ${name} ${Action}`
      default:
        return `${Type} ${name} ${Action}`
    }
  }

  const getEventTime = (event: typeof events[0]) => {
    const date = new Date(event.time * 1000)
    return formatDistanceToNow(date, { addSuffix: true })
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <PageTitle 
          title="Docker Events" 
          subtitle="Real-time Docker system events"
        />
        
        <div className="flex items-center gap-2">
          {isConnected ? (
            <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
              <span className="w-2 h-2 bg-green-400 rounded-full mr-1 animate-pulse"></span>
              Connected
            </span>
          ) : (
            <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">
              <span className="w-2 h-2 bg-red-400 rounded-full mr-1"></span>
              Disconnected
            </span>
          )}
          
          <button
            onClick={clearEvents}
            className="btn btn-sm btn-secondary"
          >
            Clear Events
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger mb-4">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search events..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="form-control"
              />
            </div>
            
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="form-control sm:w-48"
            >
              <option value="all">All Types</option>
              <option value="container">Containers</option>
              <option value="image">Images</option>
              <option value="network">Networks</option>
              <option value="volume">Volumes</option>
              <option value="node">Nodes</option>
              <option value="service">Services</option>
            </select>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {filteredEvents.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {searchTerm || typeFilter !== 'all' 
                ? 'No events match your filters'
                : 'No events yet. Docker events will appear here as they occur.'}
            </div>
          ) : (
            filteredEvents.map((event, index) => (
              <div key={`${event.time}-${index}`} className="p-4 hover:bg-gray-50">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">
                    {EVENT_ACTION_ICONS[event.Action] || '📌'}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-sm font-medium ${EVENT_TYPE_COLORS[event.Type] || 'text-gray-600'}`}>
                        {event.Type.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {getEventTime(event)}
                      </span>
                      {event.host_id && event.host_id !== 'all' && (
                        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                          Host: {event.host_id}
                        </span>
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-900 mb-1">
                      {getEventDescription(event)}
                    </p>
                    
                    {event.Actor.Attributes.image && (
                      <p className="text-xs text-gray-500">
                        Image: {event.Actor.Attributes.image}
                      </p>
                    )}
                    
                    {Object.keys(event.Actor.Attributes).length > 2 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                          View details
                        </summary>
                        <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                          {JSON.stringify(event.Actor.Attributes, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {filteredEvents.length > 0 && (
          <div className="card-footer text-center text-sm text-gray-500">
            Showing {filteredEvents.length} of {events.length} events
          </div>
        )}
      </div>
    </div>
  )
}