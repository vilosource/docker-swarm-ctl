import { api } from './client'
import { WizardType, WizardStatus } from '@/types'

export interface WizardState {
  [key: string]: any
}

export interface WizardInstance {
  id: string
  user_id: string
  wizard_type: WizardType
  version: number
  resource_id?: string
  resource_type?: string
  current_step: number
  total_steps: number
  status: WizardStatus
  state: WizardState
  metadata: Record<string, any>
  progress_percentage: number
  can_resume: boolean
  is_completed: boolean
  created_at: string
  updated_at: string
  completed_at?: string
}

export interface WizardCreate {
  wizard_type: WizardType
  resource_id?: string
  resource_type?: string
  initial_state?: WizardState
}

export interface WizardStepUpdate {
  step_data: WizardState
}

export interface WizardTestRequest {
  test_type: string
}

export interface WizardTestResult {
  success: boolean
  message: string
  details?: Record<string, any>
  error?: string
  system_info?: Record<string, any>
  docker_info?: Record<string, any>
}

export interface WizardCompletionResult {
  success: boolean
  message: string
  resource_id?: string
  resource_type?: string
  details?: Record<string, any>
}

export interface SSHKeyPair {
  private_key: string
  public_key: string
  comment: string
}

export const wizardsApi = {
  // Start a new wizard
  start: async (data: WizardCreate): Promise<WizardInstance> => {
    const response = await api.post('/wizards/start', data)
    return response.data
  },

  // Get wizard details
  get: async (wizardId: string): Promise<WizardInstance> => {
    const response = await api.get(`/wizards/${wizardId}`)
    return response.data
  },

  // List pending wizards
  listPending: async (wizardType?: WizardType): Promise<{ wizards: WizardInstance[], total: number }> => {
    const params = wizardType ? { wizard_type: wizardType } : {}
    const response = await api.get('/wizards/my-pending', { params })
    return response.data
  },

  // Update current step data
  updateStep: async (wizardId: string, stepData: WizardState): Promise<WizardInstance> => {
    const response = await api.put(`/wizards/${wizardId}/step`, { step_data: stepData })
    return response.data
  },

  // Navigate to next step
  nextStep: async (wizardId: string): Promise<WizardInstance> => {
    const response = await api.post(`/wizards/${wizardId}/next`)
    return response.data
  },

  // Navigate to previous step
  previousStep: async (wizardId: string): Promise<WizardInstance> => {
    const response = await api.post(`/wizards/${wizardId}/back`)
    return response.data
  },

  // Run step test/validation
  testStep: async (wizardId: string, testType: string): Promise<WizardTestResult> => {
    const response = await api.post(`/wizards/${wizardId}/test`, { test_type: testType })
    return response.data
  },

  // Complete wizard
  complete: async (wizardId: string): Promise<WizardCompletionResult> => {
    const response = await api.post(`/wizards/${wizardId}/complete`)
    return response.data
  },

  // Cancel wizard
  cancel: async (wizardId: string): Promise<void> => {
    await api.delete(`/wizards/${wizardId}`)
  },

  // Generate SSH key pair
  generateSSHKey: async (comment?: string): Promise<SSHKeyPair> => {
    const params = comment ? { comment } : {}
    const response = await api.post('/wizards/generate-ssh-key', null, { params })
    return response.data
  }
}