import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { wizardsApi, WizardInstance } from '@/api/wizards'
import { WizardModal, WizardStepProps } from './WizardModal'
import { WizardType } from '@/types'
import { useToast } from '@/hooks/useToast'

// Import all step components
import { ConnectionDetailsStep } from './steps/ConnectionDetailsStep'
import { AuthenticationStep } from './steps/AuthenticationStep'
import { SSHTestStep } from './steps/SSHTestStep'
import { DockerTestStep } from './steps/DockerTestStep'
import { ConfirmationStep } from './steps/ConfirmationStep'

interface SSHHostWizardProps {
  open: boolean
  onClose: () => void
  wizardId?: string
  onComplete?: (hostId: string) => void
}

const wizardSteps = [
  {
    label: 'Connection Details',
    component: ConnectionDetailsStep,
    validation: (state: any) => {
      if (!state.host_url) return 'Host URL is required'
      if (!state.connection_name) return 'Connection name is required'
      if (!state.host_type) return 'Host type is required'
      if (!state.host_url.startsWith('ssh://')) return 'Host URL must start with ssh://'
      return null
    }
  },
  {
    label: 'Authentication',
    component: AuthenticationStep,
    validation: (state: any) => {
      if (!state.auth_method) return 'Authentication method is required'
      if (state.auth_method === 'existing_key' && !state.private_key) {
        return 'Private key is required'
      }
      if (state.auth_method === 'password' && !state.password) {
        return 'Password is required'
      }
      return null
    }
  },
  {
    label: 'Test SSH Connection',
    component: SSHTestStep
  },
  {
    label: 'Test Docker Access',
    component: DockerTestStep
  },
  {
    label: 'Confirmation',
    component: ConfirmationStep
  }
]

export const SSHHostWizard: React.FC<SSHHostWizardProps> = ({
  open,
  onClose,
  wizardId,
  onComplete
}) => {
  const [wizard, setWizard] = useState<WizardInstance | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  // Create wizard mutation
  const createWizardMutation = useMutation({
    mutationFn: () => wizardsApi.start({
      wizard_type: 'ssh_host_setup' as WizardType,
      initial_state: {}
    }),
    onSuccess: (data) => {
      setWizard(data)
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to start wizard')
    }
  })

  // Get wizard mutation
  const getWizardMutation = useMutation({
    mutationFn: (id: string) => wizardsApi.get(id),
    onSuccess: (data) => {
      setWizard(data)
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to load wizard')
    }
  })

  // Update step mutation
  const updateStepMutation = useMutation({
    mutationFn: ({ wizardId, stepData }: { wizardId: string, stepData: any }) =>
      wizardsApi.updateStep(wizardId, stepData),
    onSuccess: (data) => {
      setWizard(data)
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to update wizard')
    }
  })

  // Navigate mutation
  const navigateMutation = useMutation({
    mutationFn: ({ wizardId, direction }: { wizardId: string, direction: 'next' | 'back' }) =>
      direction === 'next' ? wizardsApi.nextStep(wizardId) : wizardsApi.previousStep(wizardId),
    onSuccess: (data) => {
      setWizard(data)
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to navigate')
    }
  })

  // Complete wizard mutation
  const completeMutation = useMutation({
    mutationFn: (wizardId: string) => wizardsApi.complete(wizardId),
    onSuccess: (data) => {
      showToast('SSH host setup completed successfully', 'success')
      queryClient.invalidateQueries({ queryKey: ['hosts'] })
      if (onComplete && data.resource_id) {
        onComplete(data.resource_id)
      }
      handleClose()
    },
    onError: (err: any) => {
      setError(err.response?.data?.error?.message || 'Failed to complete wizard')
    }
  })

  // Cancel wizard mutation
  const cancelMutation = useMutation({
    mutationFn: (wizardId: string) => wizardsApi.cancel(wizardId),
    onSuccess: () => {
      showToast('Wizard cancelled', 'info')
      handleClose()
    },
    onError: (err: any) => {
      showToast('Failed to cancel wizard', 'error')
    }
  })

  // Initialize wizard on mount
  React.useEffect(() => {
    if (open) {
      if (wizardId) {
        getWizardMutation.mutate(wizardId)
      } else {
        createWizardMutation.mutate()
      }
    }
  }, [open, wizardId])

  const handleNavigate = async (direction: 'next' | 'back') => {
    if (!wizard) return

    navigateMutation.mutate({
      wizardId: wizard.id,
      direction
    })
  }

  const handleComplete = async () => {
    if (!wizard) return

    completeMutation.mutate(wizard.id)
  }

  const handleCancel = () => {
    if (wizard && wizard.status === 'in_progress') {
      cancelMutation.mutate(wizard.id)
    } else {
      handleClose()
    }
  }

  const handleClose = () => {
    setWizard(null)
    setError(null)
    onClose()
  }

  const isLoading = createWizardMutation.isPending ||
    getWizardMutation.isPending ||
    updateStepMutation.isPending ||
    navigateMutation.isPending ||
    completeMutation.isPending

  const handleUpdateState = async (wizardId: string, stepData: any) => {
    await updateStepMutation.mutateAsync({ wizardId, stepData })
  }

  return (
    <WizardModal
      open={open}
      onClose={handleClose}
      wizard={wizard}
      steps={wizardSteps}
      title="Setup SSH Host"
      onNavigate={handleNavigate}
      onComplete={handleComplete}
      onCancel={handleCancel}
      onUpdateState={handleUpdateState}
      isLoading={isLoading}
      error={error}
    />
  )
}