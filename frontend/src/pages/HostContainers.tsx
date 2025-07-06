import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { containersApi } from '@/api/containers'
import { hostsApi } from '@/api/hosts'
import { Container } from '@/types'
import ContainerList from '@/components/containers/ContainerList'
import CreateContainerModal from '@/components/containers/CreateContainerModal'
import { useAuthStore } from '@/store/authStore'
import PageTitle from '@/components/common/PageTitle'

export default function HostContainers() {
  const { hostId } = useParams<{ hostId: string }>()
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [showAll, setShowAll] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  const canManageContainers = user?.role === 'admin' || user?.role === 'operator'
  
  // Fetch host details
  const { data: host } = useQuery({
    queryKey: ['hosts', hostId],
    queryFn: () => hostsApi.get(hostId!),
    enabled: !!hostId,
  })
  
  // Fetch containers for this specific host
  const { data: containers = [], isLoading } = useQuery({
    queryKey: ['containers', hostId, showAll],
    queryFn: async () => {
      const response = await containersApi.list(showAll, hostId)
      return response.data
    },
    enabled: !!hostId,
  })
  
  const startMutation = useMutation({
    mutationFn: ({ id }: { id: string }) => containersApi.start(id, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['containers', hostId] })
    },
  })
  
  const stopMutation = useMutation({
    mutationFn: ({ id }: { id: string }) => containersApi.stop(id, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['containers', hostId] })
    },
  })
  
  const removeMutation = useMutation({
    mutationFn: ({ id }: { id: string }) => containersApi.remove(id, false, false, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['containers', hostId] })
    },
  })
  
  const handleStart = async (container: Container) => {
    await startMutation.mutateAsync({ id: container.id })
  }
  
  const handleStop = async (container: Container) => {
    await stopMutation.mutateAsync({ id: container.id })
  }
  
  const handleRemove = async (container: Container) => {
    if (confirm(`Are you sure you want to remove ${container.name}?`)) {
      await removeMutation.mutateAsync({ id: container.id })
    }
  }
  
  if (isLoading || !host) {
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
        title={`${host.name} - Containers`} 
        breadcrumb={[
          { title: 'Hosts', href: '/hosts' },
          { title: host.name, href: '#' },
          { title: 'Containers' }
        ]}
      />
      
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <div className="row mb-2">
                <div className="col-sm-8">
                  <div className="d-flex align-items-center">
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
                    <span className="ms-3 text-muted">
                      <i className="mdi mdi-server me-1"></i>
                      {host.host_url}
                    </span>
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
          hostId={hostId}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            queryClient.invalidateQueries({ queryKey: ['containers', hostId] })
          }}
        />
      )}
    </>
  )
}