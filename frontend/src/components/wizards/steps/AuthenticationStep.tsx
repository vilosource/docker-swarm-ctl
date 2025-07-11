import React, { useState } from 'react'
import { WizardStepProps } from '../WizardModal'
import { useMutation } from '@tanstack/react-query'
import { wizardsApi } from '@/api/wizards'

export const AuthenticationStep: React.FC<WizardStepProps> = ({
  state,
  onStateChange,
  error
}) => {
  const [keyComment, setKeyComment] = useState('')
  const [generatedKey, setGeneratedKey] = useState<{ private_key: string, public_key: string } | null>(null)

  const generateKeyMutation = useMutation({
    mutationFn: (comment?: string) => wizardsApi.generateSSHKey(comment),
    onSuccess: (data) => {
      setGeneratedKey(data)
      onStateChange({
        private_key: data.private_key,
        public_key: data.public_key,
        key_generated: true
      })
    }
  })

  const handleAuthMethodChange = (method: string) => {
    onStateChange({
      auth_method: method,
      private_key: method === 'new_key' && generatedKey ? generatedKey.private_key : '',
      public_key: method === 'new_key' && generatedKey ? generatedKey.public_key : '',
      password: '',
      key_passphrase: ''
    })
    if (method !== 'new_key') {
      setGeneratedKey(null)
    }
  }

  const handleGenerateKey = () => {
    const comment = keyComment || `docker-control-platform@${new Date().toISOString().split('T')[0]}`
    generateKeyMutation.mutate(comment)
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        onStateChange({ private_key: content })
      }
      reader.readAsText(file)
    }
  }

  return (
    <div>
      <p className="text-muted mb-3">
        Choose how to authenticate with the SSH server.
      </p>

      <div className="mb-4">
        <label className="form-label">Authentication Method</label>
        <div>
          <div className="form-check">
            <input
              className="form-check-input"
              type="radio"
              name="authMethod"
              id="newKey"
              value="new_key"
              checked={state.auth_method === 'new_key'}
              onChange={(e) => handleAuthMethodChange(e.target.value)}
            />
            <label className="form-check-label" htmlFor="newKey">
              Generate new SSH key pair
            </label>
          </div>
          <div className="form-check">
            <input
              className="form-check-input"
              type="radio"
              name="authMethod"
              id="existingKey"
              value="existing_key"
              checked={state.auth_method === 'existing_key'}
              onChange={(e) => handleAuthMethodChange(e.target.value)}
            />
            <label className="form-check-label" htmlFor="existingKey">
              Use existing SSH private key
            </label>
          </div>
          <div className="form-check">
            <input
              className="form-check-input"
              type="radio"
              name="authMethod"
              id="password"
              value="password"
              checked={state.auth_method === 'password'}
              onChange={(e) => handleAuthMethodChange(e.target.value)}
            />
            <label className="form-check-label" htmlFor="password">
              Use password authentication
            </label>
          </div>
        </div>
      </div>

      {state.auth_method === 'new_key' && (
        <div className="border rounded p-3">
          <h6 className="mb-3">Generate ED25519 SSH Key Pair</h6>
          
          <div className="mb-3">
            <label className="form-label">Key Comment</label>
            <input
              type="text"
              className="form-control"
              value={keyComment}
              onChange={(e) => setKeyComment(e.target.value)}
              placeholder="docker-control-platform@hostname"
            />
            <small className="text-muted">Optional: Comment to identify this key</small>
          </div>

          <button
            className="btn btn-primary mb-3"
            onClick={handleGenerateKey}
            disabled={generateKeyMutation.isPending || !!generatedKey}
          >
            {generateKeyMutation.isPending && (
              <span className="spinner-border spinner-border-sm me-1"></span>
            )}
            <i className="mdi mdi-key me-1"></i>
            {generatedKey ? 'Key Generated' : 'Generate SSH Key'}
          </button>

          {generatedKey && (
            <div>
              <div className="alert alert-success">
                <i className="mdi mdi-check-circle-outline me-1"></i>
                SSH key pair generated successfully! The private key has been stored securely.
              </div>
              
              <div className="mb-3">
                <label className="form-label">Public Key (add this to ~/.ssh/authorized_keys on the target host):</label>
                <textarea
                  className="form-control font-monospace"
                  value={generatedKey.public_key}
                  readOnly
                  rows={3}
                />
              </div>

              <div className="alert alert-info">
                <i className="mdi mdi-information-outline me-1"></i>
                Copy the public key above and add it to the authorized_keys file on your Docker host.
                You can do this by running:
                <br />
                <code className="d-block mt-2 p-2 bg-light">{`echo "${generatedKey.public_key}" >> ~/.ssh/authorized_keys`}</code>
              </div>
            </div>
          )}
        </div>
      )}

      {state.auth_method === 'existing_key' && (
        <div className="border rounded p-3">
          <h6 className="mb-3">Provide SSH Private Key</h6>

          <div className="mb-3">
            <label htmlFor="keyFile" className="btn btn-outline-primary">
              <i className="mdi mdi-upload me-1"></i>
              Upload Private Key File
            </label>
            <input
              type="file"
              id="keyFile"
              className="d-none"
              accept=".pem,.key,id_rsa,id_ed25519,id_ecdsa"
              onChange={handleFileUpload}
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Private Key</label>
            <textarea
              className="form-control font-monospace"
              value={state.private_key || ''}
              onChange={(e) => onStateChange({ private_key: e.target.value })}
              rows={10}
              placeholder="-----BEGIN OPENSSH PRIVATE KEY-----
..."
            />
            <small className="text-muted">Paste your SSH private key here or upload a file</small>
          </div>

          <div className="mb-3">
            <label className="form-label">Key Passphrase</label>
            <input
              type="password"
              className="form-control"
              value={state.key_passphrase || ''}
              onChange={(e) => onStateChange({ key_passphrase: e.target.value })}
              placeholder="Optional"
            />
            <small className="text-muted">Enter passphrase if the key is encrypted</small>
          </div>
        </div>
      )}

      {state.auth_method === 'password' && (
        <div className="border rounded p-3">
          <h6 className="mb-3">Password Authentication</h6>

          <div className="alert alert-warning">
            <i className="mdi mdi-alert-outline me-1"></i>
            Password authentication is less secure than key-based authentication.
            Consider using SSH keys for production environments.
          </div>

          <div className="mb-3">
            <label className="form-label">SSH Password *</label>
            <input
              type="password"
              className="form-control"
              value={state.password || ''}
              onChange={(e) => onStateChange({ password: e.target.value })}
              required
            />
          </div>
        </div>
      )}
    </div>
  )
}