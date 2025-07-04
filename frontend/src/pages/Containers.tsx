import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { containersApi } from '@/api/containers'
import { Container } from '@/types'
import ContainerList from '@/components/containers/ContainerList'
import CreateContainerModal from '@/components/containers/CreateContainerModal'
import { useAuthStore } from '@/store/authStore'
import PageTitle from '@/components/common/PageTitle'

export default function Containers() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [showAll, setShowAll] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  const canManageContainers = user?.role === 'admin' || user?.role === 'operator'
  
  const { data: containers = [], isLoading } = useQuery({
    queryKey: ['containers', showAll],
    queryFn: async () => {
      const response = await containersApi.list(showAll)
      return response.data
    },
  })
  
  const startMutation = useMutation({
    mutationFn: containersApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['containers'] })
    },
  })
  
  const stopMutation = useMutation({
    mutationFn: containersApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['containers'] })
    },
  })
  
  const removeMutation = useMutation({
    mutationFn: (id: string) => containersApi.remove(id, false, false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['containers'] })
    },
  })
  
  const handleStart = async (container: Container) => {
    await startMutation.mutateAsync(container.id)
  }
  
  const handleStop = async (container: Container) => {
    await stopMutation.mutateAsync(container.id)
  }
  
  const handleRemove = async (container: Container) => {
    if (confirm(`Are you sure you want to remove ${container.name}?`)) {
      await removeMutation.mutateAsync(container.id)
    }
  }
  
  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }
  
  return (
    <>
      <PageTitle 
        title="Containers" 
        breadcrumb={[
          { title: 'Docker', href: '#' },
          { title: 'Containers' }
        ]}
      />
      
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <div className="row mb-2">
                <div className="col-sm-8">
                  <div className="form-check form-check-inline">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      id="showAllContainers"
                      checked={showAll}
                      onChange={(e) => setShowAll(e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="showAllContainers">
                      Show all containers
                    </label>
                  </div>
                </div>
                <div className="col-sm-4">
                  <div className="text-sm-end">
                    {canManageContainers && (
                      <button
                        onClick={() => setShowCreateModal(true)}
                        className="btn btn-primary mb-2"
                      >
                        <i className="mdi mdi-plus-circle me-2"></i> Create Container
                      </button>
                    )}
                  </div>
                </div>
              </div>
              
              <ContainerList
                containers={containers}
                onStart={handleStart}
                onStop={handleStop}
                onRemove={handleRemove}
                canManage={canManageContainers}
              />
            </div>
          </div>
        </div>
      </div>
      
      {showCreateModal && (
        <CreateContainerModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            queryClient.invalidateQueries({ queryKey: ['containers'] })
          }}
        />
      )}
    </>
  )
}