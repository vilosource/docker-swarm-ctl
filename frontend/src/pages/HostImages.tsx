import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { imagesApi } from '@/api/images'
import { hostsApi } from '@/api/hosts'
import { Image } from '@/types'
import { formatBytes, formatDate } from '@/utils/format'
import { useAuthStore } from '@/store/authStore'
import PageTitle from '@/components/common/PageTitle'

export default function HostImages() {
  const { hostId } = useParams<{ hostId: string }>()
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set())
  
  const canManageImages = user?.role === 'admin' || user?.role === 'operator'
  
  // Fetch host details
  const { data: host } = useQuery({
    queryKey: ['hosts', hostId],
    queryFn: () => hostsApi.get(hostId!),
    enabled: !!hostId,
  })
  
  // Fetch images for this specific host
  const { data: images = [], isLoading } = useQuery({
    queryKey: ['images', hostId],
    queryFn: async () => {
      const response = await imagesApi.list(hostId)
      return response.data
    },
    enabled: !!hostId,
  })
  
  const removeMutation = useMutation({
    mutationFn: ({ id }: { id: string }) => imagesApi.remove(id, false, hostId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images', hostId] })
      setSelectedImages(new Set())
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to remove image'
      alert(errorMessage)
    },
  })
  
  const handleRemove = async (image: Image) => {
    const name = image.tags[0] || image.id.substring(0, 12)
    if (confirm(`Are you sure you want to remove image ${name}?`)) {
      try {
        await removeMutation.mutateAsync({ id: image.id })
      } catch (error) {
        // Error is already handled by onError in the mutation
      }
    }
  }
  
  const handleRemoveSelected = async () => {
    if (selectedImages.size === 0) return
    
    if (confirm(`Are you sure you want to remove ${selectedImages.size} selected images?`)) {
      for (const imageId of selectedImages) {
        try {
          await removeMutation.mutateAsync({ id: imageId })
        } catch (error) {
          // Error is already handled by onError in the mutation
          // Continue with next image
        }
      }
    }
  }
  
  const toggleImageSelection = (imageId: string) => {
    const newSelection = new Set(selectedImages)
    if (newSelection.has(imageId)) {
      newSelection.delete(imageId)
    } else {
      newSelection.add(imageId)
    }
    setSelectedImages(newSelection)
  }
  
  const toggleAllSelection = () => {
    if (selectedImages.size === images.length) {
      setSelectedImages(new Set())
    } else {
      setSelectedImages(new Set(images.map(img => img.id)))
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
        title={`${host.name} - Images`} 
        breadcrumb={[
          { title: 'Hosts', href: '/hosts' },
          { title: host.name, href: '#' },
          { title: 'Images' }
        ]}
      />
      
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <div className="row mb-2">
                <div className="col-sm-8">
                  <span className="text-muted">
                    <i className="mdi mdi-server me-1"></i>
                    {host.host_url}
                  </span>
                </div>
                <div className="col-sm-4">
                  <div className="text-sm-end">
                    {canManageImages && selectedImages.size > 0 && (
                      <button
                        onClick={handleRemoveSelected}
                        className="btn btn-danger mb-2"
                        disabled={removeMutation.isPending}
                      >
                        <i className="mdi mdi-delete me-2"></i> 
                        Remove Selected ({selectedImages.size})
                      </button>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="table-responsive">
                <table className="table table-centered table-hover mb-0">
                  <thead>
                    <tr>
                      {canManageImages && (
                        <th style={{ width: '40px' }}>
                          <div className="form-check">
                            <input
                              type="checkbox"
                              className="form-check-input"
                              checked={selectedImages.size === images.length && images.length > 0}
                              onChange={toggleAllSelection}
                            />
                          </div>
                        </th>
                      )}
                      <th>Repository</th>
                      <th>Tag</th>
                      <th>Image ID</th>
                      <th>Created</th>
                      <th>Size</th>
                      {canManageImages && <th>Action</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {images.map((image) => (
                      <tr key={image.id}>
                        {canManageImages && (
                          <td>
                            <div className="form-check">
                              <input
                                type="checkbox"
                                className="form-check-input"
                                checked={selectedImages.has(image.id)}
                                onChange={() => toggleImageSelection(image.id)}
                              />
                            </div>
                          </td>
                        )}
                        <td>
                          {image.tags.length > 0 ? (
                            <span className="font-family-monospace">
                              {image.tags[0].split(':')[0]}
                            </span>
                          ) : (
                            <span className="text-muted">&lt;none&gt;</span>
                          )}
                        </td>
                        <td>
                          {image.tags.length > 0 ? (
                            <span className="badge badge-soft-primary">
                              {image.tags[0].split(':')[1] || 'latest'}
                            </span>
                          ) : (
                            <span className="text-muted">&lt;none&gt;</span>
                          )}
                        </td>
                        <td>
                          <code>{image.id.substring(0, 12)}</code>
                        </td>
                        <td>{formatDate(image.created)}</td>
                        <td>{formatBytes(image.size)}</td>
                        {canManageImages && (
                          <td>
                            <button
                              onClick={() => handleRemove(image)}
                              className="btn btn-sm btn-danger"
                              disabled={removeMutation.isPending}
                            >
                              <i className="mdi mdi-delete"></i>
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {images.length === 0 && (
                  <div className="text-center py-4">
                    <p className="text-muted mb-0">No images found on this host</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}