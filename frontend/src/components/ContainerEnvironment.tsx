import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { containersApi } from '@/api/containers'

interface ContainerEnvironmentProps {
  containerId: string
  hostId?: string
}

const ContainerEnvironment: React.FC<ContainerEnvironmentProps> = ({ containerId, hostId }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['container-inspect', containerId, hostId],
    queryFn: () => containersApi.inspect(containerId, hostId),
    select: (response) => response.data
  })

  if (isLoading) {
    return (
      <div className="text-center py-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        Failed to load container environment: {(error as Error).message}
      </div>
    )
  }

  if (!data?.environment || data.environment.length === 0) {
    return (
      <div className="text-muted text-center py-4">
        No environment variables found
      </div>
    )
  }

  // Parse environment variables from KEY=VALUE format
  const envVars = data.environment.map(env => {
    const [key, ...valueParts] = env.split('=')
    return {
      key,
      value: valueParts.join('=') // Handle values that contain '='
    }
  })

  return (
    <div className="table-responsive">
      <table className="table table-striped mb-0">
        <thead>
          <tr>
            <th style={{ width: '40%' }}>Variable</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {envVars.map((envVar, index) => (
            <tr key={index}>
              <td className="font-monospace">
                <strong>{envVar.key}</strong>
              </td>
              <td className="font-monospace text-break">
                {envVar.value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ContainerEnvironment