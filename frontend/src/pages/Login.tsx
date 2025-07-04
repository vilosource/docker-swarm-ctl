import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      await login(email, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="account-pages mt-5 mb-5">
      <div className="container">
        <div className="row justify-content-center">
          <div className="col-md-8 col-lg-6 col-xl-4">
            <div className="text-center">
              <a href="/">
                <img src="/assets/images/logo-dark.png" alt="" height="22" className="mx-auto" />
              </a>
              <p className="text-muted mt-2 mb-4">Docker Control Platform</p>
            </div>
            
            <div className="card">
              <div className="card-body p-4">
                <div className="text-center mb-4">
                  <h4 className="text-uppercase mt-0">Sign In</h4>
                </div>
                
                {error && (
                  <div className="alert alert-danger" role="alert">
                    <i className="mdi mdi-block-helper me-2"></i> {error}
                  </div>
                )}
                
                <form onSubmit={handleSubmit}>
                  <div className="mb-3">
                    <label htmlFor="emailaddress" className="form-label">Email address</label>
                    <input 
                      className="form-control" 
                      type="email" 
                      id="emailaddress" 
                      required 
                      placeholder="Enter your email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                  
                  <div className="mb-3">
                    <label htmlFor="password" className="form-label">Password</label>
                    <input 
                      className="form-control" 
                      type="password" 
                      required 
                      id="password" 
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                  
                  <div className="mb-3">
                    <div className="form-check">
                      <input type="checkbox" className="form-check-input" id="checkbox-signin" />
                      <label className="form-check-label" htmlFor="checkbox-signin">
                        Remember me
                      </label>
                    </div>
                  </div>
                  
                  <div className="mb-3 d-grid text-center">
                    <button 
                      className="btn btn-primary" 
                      type="submit"
                      disabled={loading}
                    >
                      {loading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                          Loading...
                        </>
                      ) : (
                        'Sign In'
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
            
            <div className="row mt-3">
              <div className="col-12 text-center">
                <p className="text-muted">
                  Default credentials: <br />
                  <code>admin@localhost.local / changeme123</code>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}