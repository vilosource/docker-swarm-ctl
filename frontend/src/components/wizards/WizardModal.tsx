import React, { useState, useEffect } from 'react'
import { WizardInstance, WizardState } from '@/api/wizards'

interface WizardStep {
  label: string
  component: React.ComponentType<WizardStepProps>
  validation?: (state: WizardState) => string | null
}

export interface WizardStepProps {
  state: WizardState
  onStateChange: (updates: Partial<WizardState>) => void
  onTest?: (testType: string) => Promise<any>
  testResult?: any
  isLoading?: boolean
  error?: string
}

interface WizardModalProps {
  open: boolean
  onClose: () => void
  wizard: WizardInstance | null
  steps: WizardStep[]
  title: string
  onNavigate: (direction: 'next' | 'back') => void
  onComplete: () => void
  onCancel: () => void
  onUpdateState: (wizardId: string, stepData: WizardState) => Promise<void>
  isLoading?: boolean
  error?: string | null
}

export const WizardModal: React.FC<WizardModalProps> = ({
  open,
  onClose,
  wizard,
  steps,
  title,
  onNavigate,
  onComplete,
  onCancel,
  onUpdateState,
  isLoading = false,
  error = null
}) => {
  const [localState, setLocalState] = useState<WizardState>({})
  const [stepError, setStepError] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<any>(null)

  useEffect(() => {
    if (wizard?.state) {
      setLocalState(wizard.state)
    }
  }, [wizard?.state])

  if (!wizard || !open) {
    return null
  }

  const currentStep = wizard.current_step
  const CurrentStepComponent = steps[currentStep]?.component

  const handleStateChange = async (updates: Partial<WizardState>) => {
    const newState = { ...localState, ...updates }
    setLocalState(newState)
    setStepError(null)
    
    // Update wizard state in backend
    if (wizard) {
      try {
        await onUpdateState(wizard.id, newState)
      } catch (err) {
        console.error('Failed to update wizard state:', err)
      }
    }
  }

  const handleNext = () => {
    // Validate current step
    const validation = steps[currentStep]?.validation
    if (validation) {
      const validationError = validation(localState)
      if (validationError) {
        setStepError(validationError)
        return
      }
    }

    onNavigate('next')
  }

  const handleBack = () => {
    onNavigate('back')
  }

  const handleComplete = () => {
    // Validate final step
    const validation = steps[currentStep]?.validation
    if (validation) {
      const validationError = validation(localState)
      if (validationError) {
        setStepError(validationError)
        return
      }
    }

    onComplete()
  }

  const handleTest = async (testType: string) => {
    setTestResult(null)
    // This would be implemented by the parent component
    // For now, just a placeholder
  }

  const isFirstStep = currentStep === 0
  const isLastStep = currentStep === wizard.total_steps - 1

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg modal-dialog-scrollable">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">{title}</h5>
            <button 
              type="button" 
              className="btn-close" 
              onClick={onClose}
              disabled={isLoading}
            ></button>
          </div>

          <div className="modal-body">
            {/* Progress Steps */}
            <div className="mb-4">
              <div className="d-flex justify-content-between align-items-center">
                {steps.map((step, index) => (
                  <div key={index} className="text-center flex-fill">
                    <div className={`rounded-circle d-inline-flex align-items-center justify-content-center ${
                      index === currentStep ? 'bg-primary text-white' : 
                      index < currentStep ? 'bg-success text-white' : 'bg-light text-muted'
                    }`} style={{ width: '40px', height: '40px' }}>
                      {index < currentStep ? <i className="mdi mdi-check"></i> : index + 1}
                    </div>
                    <div className={`small mt-1 ${index === currentStep ? 'text-primary fw-bold' : ''}`}>
                      {step.label}
                    </div>
                  </div>
                ))}
              </div>
              <div className="progress mt-3" style={{ height: '4px' }}>
                <div 
                  className="progress-bar" 
                  style={{ width: `${((currentStep + 1) / wizard.total_steps) * 100}%` }}
                ></div>
              </div>
            </div>

            {error && (
              <div className="alert alert-danger mb-3">
                <i className="mdi mdi-alert-circle-outline me-1"></i>
                {error}
              </div>
            )}

            {stepError && (
              <div className="alert alert-warning mb-3">
                <i className="mdi mdi-alert-outline me-1"></i>
                {stepError}
              </div>
            )}

            <div style={{ minHeight: '300px' }}>
              {CurrentStepComponent && (
                <CurrentStepComponent
                  state={{ ...localState, wizard_id: wizard.id }}
                  onStateChange={handleStateChange}
                  onTest={handleTest}
                  testResult={testResult}
                  isLoading={isLoading}
                  error={stepError}
                />
              )}
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={isLoading}
            >
              Cancel
            </button>
            <div className="ms-auto">
              <button
                type="button"
                className="btn btn-light me-2"
                onClick={handleBack}
                disabled={isFirstStep || isLoading}
              >
                <i className="mdi mdi-chevron-left"></i> Back
              </button>
              {!isLastStep ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleNext}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="spinner-border spinner-border-sm me-1"></span>
                  ) : null}
                  Next <i className="mdi mdi-chevron-right"></i>
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={handleComplete}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="spinner-border spinner-border-sm me-1"></span>
                  ) : null}
                  Complete
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}