import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { imagesApi } from '@/api/images'
import { useAuthStore } from '@/store/authStore'
import { format } from 'date-fns'
import PageTitle from '@/components/common/PageTitle'

export default function Images() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [pullModalOpen, setPullModalOpen] = useState(false)
  const [pullForm, setPullForm] = useState({ repository: '', tag: 'latest' })
  
  const canManageImages = user?.role === 'admin' || user?.role === 'operator'
  
  const { data: images = [], isLoading } = useQuery({
    queryKey: ['images'],
    queryFn: async () => {
      const response = await imagesApi.list()
      return response.data
    },
  })
  
  const removeMutation = useMutation({
    mutationFn: (id: string) => imagesApi.remove(id, false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images'] })
    },
  })
  
  const pullMutation = useMutation({
    mutationFn: imagesApi.pull,
    onSuccess: () => {
      setPullModalOpen(false)
      setPullForm({ repository: '', tag: 'latest' })
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['images'] })
      }, 2000)
    },
  })
  
  const handleRemove = async (id: string) => {
    if (confirm('Are you sure you want to remove this image?')) {
      await removeMutation.mutateAsync(id)
    }
  }
  
  const handlePull = async (e: React.FormEvent) => {
    e.preventDefault()
    await pullMutation.mutateAsync({
      repository: pullForm.repository,
      tag: pullForm.tag,
    })
  }
  
  const formatSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`
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
        title="Images" 
        breadcrumb={[
          { title: 'Docker', href: '#' },
          { title: 'Images' }
        ]}
      />
      
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <div className="row mb-2">
                <div className="col-sm-8">
                  <h5 className="mb-0">Docker Images</h5>
                </div>
                <div className="col-sm-4">
                  <div className="text-sm-end">
                    {canManageImages && (
                      <button
                        onClick={() => setPullModalOpen(true)}
                        className="btn btn-primary mb-2"
                      >
                        <i className="mdi mdi-download me-2"></i> Pull Image
                      </button>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="table-responsive">
                <table className="table table-centered table-nowrap table-striped">
                  <thead>
                    <tr>
                      <th>Repository:Tag</th>
                      <th>Image ID</th>
                      <th>Created</th>
                      <th>Size</th>
                      {canManageImages && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {images.map((image) => (
                      <tr key={image.id}>
                        <td>
                          <div className="fw-medium">
                            {image.tags.length > 0 ? image.tags.join(', ') : '<none>:<none>'}
                          </div>
                        </td>
                        <td>
                          <code className="text-muted">{image.id.substring(0, 12)}</code>
                        </td>
                        <td>{format(new Date(image.created), 'PPp')}</td>
                        <td>{formatSize(image.size)}</td>
                        {canManageImages && (
                          <td>
                            <button
                              onClick={() => handleRemove(image.id)}
                              className="btn btn-sm btn-danger"
                              title="Remove image"
                            >
                              <i className="mdi mdi-delete"></i>
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                    
                    {images.length === 0 && (
                      <tr>
                        <td colSpan={canManageImages ? 5 : 4} className="text-center text-muted py-4">
                          No images found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Pull Modal */}
      {pullModalOpen && (
        <>
          <div className="modal fade show d-block" tabIndex={-1}>
            <div className="modal-dialog modal-dialog-centered">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">Pull Image</h5>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={() => setPullModalOpen(false)}
                    aria-label="Close"
                  ></button>
                </div>
                <form onSubmit={handlePull}>
                  <div className="modal-body">
                    <div className="mb-3">
                      <label className="form-label">
                        Repository <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className="form-control"
                        required
                        value={pullForm.repository}
                        onChange={(e) => setPullForm({ ...pullForm, repository: e.target.value })}
                        placeholder="nginx"
                      />
                    </div>
                    
                    <div className="mb-3">
                      <label className="form-label">Tag</label>
                      <input
                        type="text"
                        className="form-control"
                        value={pullForm.tag}
                        onChange={(e) => setPullForm({ ...pullForm, tag: e.target.value })}
                        placeholder="latest"
                      />
                    </div>
                    
                    {pullMutation.isError && (
                      <div className="alert alert-danger mb-0">
                        <i className="mdi mdi-alert-circle me-2"></i>
                        {(pullMutation.error as any)?.response?.data?.error?.message || 'Failed to pull image'}
                      </div>
                    )}
                    
                    {pullMutation.isSuccess && (
                      <div className="alert alert-success mb-0">
                        <i className="mdi mdi-check-circle me-2"></i>
                        Image pull started. It may take a few moments to complete.
                      </div>
                    )}
                  </div>
                  
                  <div className="modal-footer">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setPullModalOpen(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={pullMutation.isPending}
                    >
                      {pullMutation.isPending ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          Pulling...
                        </>
                      ) : (
                        <>
                          <i className="mdi mdi-download me-2"></i>
                          Pull
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show"></div>
        </>
      )}
    </>
  )
}