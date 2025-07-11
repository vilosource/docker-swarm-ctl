import React, { useState } from 'react'
import { WizardStepProps } from '../WizardModal'
import { useMutation } from '@tanstack/react-query'
import { wizardsApi } from '@/api/wizards'

export const SSHTestStep: React.FC<WizardStepProps> = ({
  state,
  onStateChange,
  error
}) => {
  const [testResult, setTestResult] = useState<any>(null)
  const wizardId = state.wizard_id

  const testSSHMutation = useMutation({
    mutationFn: () => {
      if (!wizardId) throw new Error('Wizard ID not found')
      return wizardsApi.testStep(wizardId, 'ssh')
    },
    onSuccess: (data) => {
      setTestResult(data)
      if (data.success) {
        onStateChange({ ssh_test_passed: true })
      }
    }
  })

  const handleTest = () => {
    setTestResult(null)
    testSSHMutation.mutate()
  }

  return (
    <div>
      <p className="text-muted mb-3">
        Test the SSH connection to verify credentials and connectivity.
      </p>

      <div className="text-center mb-4">
        <button
          className="btn btn-primary btn-lg"
          onClick={handleTest}
          disabled={testSSHMutation.isPending}
        >
          {testSSHMutation.isPending ? (
            <>
              <span className="spinner-border spinner-border-sm me-2"></span>
              Testing Connection...
            </>
          ) : (
            <>
              <i className="mdi mdi-connection me-2"></i>
              Test SSH Connection
            </>
          )}
        </button>
      </div>

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

          {testResult.success && testResult.system_info && (
            <div className="card">
              <div className="card-body">
                <h6 className="card-title">System Information</h6>
                <dl className="row mb-0">
                  <dt className="col-sm-3">SSH User</dt>
                  <dd className="col-sm-9">{testResult.system_info.ssh_user}</dd>
                  
                  <dt className="col-sm-3">Hostname</dt>
                  <dd className="col-sm-9">{testResult.system_info.ssh_host}</dd>
                  
                  <dt className="col-sm-3">System</dt>
                  <dd className="col-sm-9">{testResult.system_info.uname}</dd>
                  
                  {testResult.system_info.os_info && (
                    <>
                      <dt className="col-sm-3">OS Info</dt>
                      <dd className="col-sm-9">
                        <pre className="mb-0 p-2 bg-light small">{testResult.system_info.os_info}</pre>
                      </dd>
                    </>
                  )}
                </dl>
              </div>
            </div>
          )}
        </div>
      )}

      {!testResult && (
        <div className="alert alert-info">
          <i className="mdi mdi-information-outline me-1"></i>
          Click the button above to test the SSH connection. This will verify:
          <ul className="mb-0 mt-2">
            <li>SSH connectivity to the host</li>
            <li>Authentication credentials</li>
            <li>Basic system information</li>
          </ul>
        </div>
      )}
    </div>
  )
}