import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { containersApi, ContainerCreateRequest } from '@/api/containers'

interface CreateContainerModalProps {
  onClose: () => void
  onSuccess: () => void
  hostId?: string
}

export default function CreateContainerModal({ onClose, onSuccess, hostId }: CreateContainerModalProps) {
  const [formData, setFormData] = useState<ContainerCreateRequest>({
    image: '',
    name: '',
    command: [],
    environment: {},
    ports: {},
    volumes: [],
    restart_policy: 'no',
  })
  
  const [error, setError] = useState('')
  
  const createMutation = useMutation({
    mutationFn: (data: ContainerCreateRequest) => containersApi.create(data, hostId),
    onSuccess: () => {
      onSuccess()
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to create container')
    },
  })
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    await createMutation.mutateAsync(formData)
  }
  
  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900">Create Container</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500"
          >
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Image *
            </label>
            <input
              type="text"
              required
              value={formData.image}
              onChange={(e) => setFormData({ ...formData, image: e.target.value })}
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="e.g., nginx:latest"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Container Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="my-container"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Restart Policy
            </label>
            <select
              value={formData.restart_policy}
              onChange={(e) => setFormData({ ...formData, restart_policy: e.target.value as any })}
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="no">No</option>
              <option value="always">Always</option>
              <option value="on-failure">On Failure</option>
              <option value="unless-stopped">Unless Stopped</option>
            </select>
          </div>
          
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}