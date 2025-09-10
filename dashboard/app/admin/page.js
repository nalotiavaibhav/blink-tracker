'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getApiBase } from '../../lib/apiBase'

export default function AdminLogin(){
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const backendBase = getApiBase()

  // If already logged in redirect; also load last used admin email (non-sensitive convenience)
  useEffect(()=>{
    const existing = localStorage.getItem('waw_admin_token') || localStorage.getItem('waw_token')
    if(existing) {
      router.replace('/admin/users')
      return
    }
    const lastEmail = localStorage.getItem('waw_last_admin_email')
    if(lastEmail) setEmail(lastEmail)
  }, [router])

  async function login(){
    if(loading) return
    setLoading(true)
    try {
      setStatus('Logging in…')
      const res = await fetch(`${backendBase}/v1/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      if(!res.ok) throw new Error('login failed')
      const data = await res.json()
      // Decode JWT payload to verify scope=admin
      const parts = data.access_token.split('.')
      if(parts.length !== 3){
        setStatus('Invalid token structure')
        return
      }
      try {
        const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')))
        if(payload.scope !== 'admin'){
          setStatus('This email is not an admin. Access denied.')
          return
        }
      } catch {
        setStatus('Unable to read token')
        return
      }
  localStorage.setItem('waw_admin_token', data.access_token)
  try { if(email) localStorage.setItem('waw_last_admin_email', email) } catch {}
      setStatus('Success')
      router.push('/admin/users')
    } catch {
      setStatus('Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="admin-center-wrapper">
      <div className="surface-card flex-col gap-md" style={{minWidth:360}}>
        <h1 style={{margin:0}}>Admin Login</h1>
        <input className="input" value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" />
        <input className="input" value={password} onChange={e=>setPassword(e.target.value)} placeholder="password" type="password" />
        <button onClick={login} className={`primary-btn ${loading ? 'loading' : ''}`} disabled={loading}>{loading ? 'Authenticating…' : 'Login'}</button>
        <small className="dim" style={{minHeight:18}}>{status}</small>
      </div>
    </main>
  )
}
