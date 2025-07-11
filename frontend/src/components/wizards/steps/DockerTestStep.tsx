import React, { useState } from 'react'
import { WizardStepProps } from '../WizardModal'
import { useMutation } from '@tanstack/react-query'
import { wizardsApi } from '@/api/wizards'

export const DockerTestStep: React.FC<WizardStepProps> = ({
  state,
  onStateChange,
  error
}) => {
  const [testResult, setTestResult] = useState<any>(null)
  const wizardId = state.wizard_id

  const testDockerMutation = useMutation({
    mutationFn: () => {
      if (!wizardId) throw new Error('Wizard ID not found')
      return wizardsApi.testStep(wizardId, 'docker')
    },
    onSuccess: (data) => {
      setTestResult(data)
      if (data.success) {
        onStateChange({ 
          docker_test_passed: true,
          docker_info: data.docker_info
        })
      }
    }
  })

  const handleTest = () => {
    setTestResult(null)
    testDockerMutation.mutate()
  }

  return (
    <div>
      <p className="text-muted mb-3">
        Test Docker API access through the SSH connection.
      </p>

      <div className="text-center mb-4">
        <button
          className="btn btn-primary btn-lg"
          onClick={handleTest}
          disabled={testDockerMutation.isPending || !state.ssh_test_passed}
        >
          {testDockerMutation.isPending ? (
            <>
              <span className="spinner-border spinner-border-sm me-2"></span>
              Testing Docker API...
            </>
          ) : (
            <>
              <i className="mdi mdi-docker me-2"></i>
              Test Docker Access
            </>
          )}
        </button>
      </div>

      {!state.ssh_test_passed && (
        <div className="alert alert-warning">
          <i className="mdi mdi-alert-outline me-1"></i>
          Please complete the SSH connection test first.
        </div>
      )}

      {testResult && (
        <div className="mt-4">
          <div className={`alert ${testResult.success ? 'alert-success' : 'alert-danger'}`}>
            <i className={`mdi ${testResult.success ? 'mdi-check-circle' : 'mdi-alert-circle'} me-1`}></i>
            {testResult.message}
            {testResult.error && (
              <div className="mt-2">
                <strong>Error:</strong> {testResult.error}
              </div>
            )}
          </div>

          {testResult.success && testResult.docker_info && (
            <div className="card">
              <div className="card-body">
                <h6 className="card-title">Docker Environment</h6>
                <dl className="row mb-0">
                  <dt className="col-sm-4">Docker Version</dt>
                  <dd className="col-sm-8">{testResult.docker_info.version}</dd>
                  
                  <dt className="col-sm-4">API Version</dt>
                  <dd className="col-sm-8">{testResult.docker_info.api_version}</dd>
                  
                  <dt className="col-sm-4">Operating System</dt>
                  <dd className="col-sm-8">{testResult.docker_info.os}</dd>
                  
                  <dt className="col-sm-4">Architecture</dt>
                  <dd className="col-sm-8">{testResult.docker_info.architecture}</dd>
                  
                  <dt className="col-sm-4">Containers</dt>
                  <dd className="col-sm-8">{testResult.docker_info.containers} total</dd>
                  
                  <dt className="col-sm-4">Images</dt>
                  <dd className="col-sm-8">{testResult.docker_info.images} total</dd>
                  
                  {testResult.docker_info.is_swarm && (
                    <>
                      <dt className="col-sm-4">Swarm Mode</dt>
                      <dd className="col-sm-8">
                        <span className="badge bg-success">Active</span>
                      </dd>
                    </>
                  )}
                </dl>
              </div>
            </div>
          )}
        </div>
      )}

      {!testResult && state.ssh_test_passed && (
        <div className="alert alert-info">
          <i className="mdi mdi-information-outline me-1"></i>
          Click the button above to test Docker API access. This will verify:
          <ul className="mb-0 mt-2">
            <li>Docker daemon is accessible via SSH</li>
            <li>Docker socket permissions are correct</li>
            <li>Docker version and configuration</li>
          </ul>
        </div>
      )}
    </div>
  )
}