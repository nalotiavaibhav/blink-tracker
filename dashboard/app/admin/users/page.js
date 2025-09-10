'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { getApiBase } from '../../../lib/apiBase'
import { formatLocalShort } from '../../../lib/format'

export default function AdminUsers(){
  const [users, setUsers] = useState([])
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const router = useRouter()
  const backendBase = getApiBase()
  const token = typeof window !== 'undefined' ? (localStorage.getItem('waw_admin_token')) : ''

  function logout(){
    localStorage.removeItem('waw_admin_token')
    localStorage.removeItem('waw_token')
    router.replace('/admin')
  }

  async function load(){
    try{
      setStatus('Loading…')
      const url = new URL(`${backendBase}/admin/users`)
      if(q) url.searchParams.set('q', q)
      const res = await fetch(url.toString(), { headers: { 'Authorization': `Bearer ${token}` } })
      if(!res.ok) throw new Error('failed')
      const data = await res.json()
      setUsers(data)
      setStatus('')
    }catch{
      setStatus('Failed to load')
    }
  }

  useEffect(()=>{ if(!token){ router.replace('/admin'); return } load() }, [q])

  return (
    <main>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:28}}>
        <h1 style={{margin:0,fontSize:22,letterSpacing:.5}}>Users</h1>
        <div style={{display:'flex',gap:12,alignItems:'center'}}>
          <input className="input" value={q} onChange={e=>setQ(e.target.value)} placeholder='Search by name/email' />
          <button onClick={logout} className="outline-btn">Logout</button>
          <small className="dim" style={{minWidth:120,textAlign:'right'}}>{status}</small>
        </div>
      </div>
      <div className="table-wrapper fade-in">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Name</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td><Link className="link-btn" href={`/admin/users/${u.id}`}>{u.id}</Link></td>
                <td>{u.email}</td>
                <td>{u.name}</td>
                <td>{formatLocalShort(u.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}
