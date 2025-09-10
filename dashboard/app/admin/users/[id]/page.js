'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getApiBase } from '../../../../lib/apiBase'
import { formatLocalShort, formatLocal } from '../../../../lib/format'

export default function AdminUserDetails(){
  const router = useRouter()
  const params = useParams()
  const userId = params?.id
  const [user, setUser] = useState(null)
  const [rows, setRows] = useState([])
  const [blinkSummary, setBlinkSummary] = useState(null)
  const [blinkSamples, setBlinkSamples] = useState([])
  const [showBlinks, setShowBlinks] = useState(false)
  const [status, setStatus] = useState('')
  const backendBase = getApiBase()
  const token = typeof window !== 'undefined' ? (localStorage.getItem('waw_admin_token')) : ''

  function logout(){
    localStorage.removeItem('waw_admin_token')
    localStorage.removeItem('waw_token')
    router.replace('/admin')
  }

  async function api(path){
    const res = await fetch(`${backendBase}${path}`, { headers: { 'Authorization': `Bearer ${token}` } })
    if(!res.ok) throw new Error('request failed')
    return res.json()
  }

  async function load(){
    try{
      setStatus('Loading…')
      const [u, s, bs, blist] = await Promise.all([
        api(`/admin/users/${userId}`),
        api(`/admin/users/${userId}/sessions`),
        api(`/admin/users/${userId}/blinks/summary`),
        api(`/admin/users/${userId}/blinks?limit=150`),
      ])
      setUser(u)
      setRows(s)
      setBlinkSummary(bs)
      setBlinkSamples(blist)
      setStatus('')
    }catch{
      setStatus('Failed to load')
    }
  }

  async function deleteUser(){
    if(!userId) return
    if(!confirm('Delete this user and all related data? This cannot be undone.')) return
    try {
      setStatus('Deleting user…')
      const res = await fetch(`${backendBase}/admin/users/${userId}`, { method:'DELETE', headers:{ 'Authorization': `Bearer ${token}` } })
      if(!res.ok) {
        const txt = await res.text()
        throw new Error(txt || 'delete failed')
      }
      setStatus('User deleted')
      setTimeout(()=>{ router.replace('/admin/users') }, 600)
    } catch (e){
      setStatus('Delete failed')
    }
  }

  useEffect(()=>{ if(!token){ router.replace('/admin'); return } if(userId) load() }, [userId])

  return (
    <main>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <div style={{display:'flex',gap:12,alignItems:'center'}}>
          <button onClick={()=>router.back()} className="outline-btn">Back</button>
          <h1 style={{margin:'0 0 0',fontSize:22,letterSpacing:.5}}>User {user?.id}</h1>
        </div>
        <div style={{display:'flex',gap:10}}>
          <button onClick={deleteUser} className="outline-btn" style={{color:'#f87171',borderColor:'#3b1818'}}>Delete</button>
          <button onClick={logout} className="outline-btn">Logout</button>
        </div>
      </div>
  <div className="user-meta-grid">
        <div className="stat">
          <h4>Email</h4>
          <div className="value" style={{fontSize:14,fontWeight:500,wordBreak:'break-all'}}>{user?.email}</div>
        </div>
        <div className="stat">
          <h4>Name</h4>
          <div className="value" style={{fontSize:14,fontWeight:500}}>{user?.name}</div>
        </div>
        <div className="stat">
          <h4>Created</h4>
          <div className="value" style={{fontSize:14,fontWeight:500}}>{formatLocalShort(user?.created_at)}</div>
        </div>
      </div>
      <div className="dim" style={{marginBottom:16}}>
        {blinkSummary && (
          <div className="section-box">
            <strong style={{color:'var(--color-text-dark)'}}>Blink Summary</strong>
            <div className="summary-grid">
              <span>Total Blinks: {blinkSummary.total_blinks}</span>
              <span>Avg / Sample: {blinkSummary.average_blinks_per_sample}</span>
              <span>Samples: {blinkSummary.total_samples}</span>
              <span>Avg CPU%: {blinkSummary.average_cpu_percent}</span>
              <span>Avg Memory MB: {blinkSummary.average_memory_mb}</span>
            </div>
            <button onClick={()=>setShowBlinks(v=>!v)} className="raw-toggle">
              {showBlinks ? 'Hide Raw Blink Samples' : 'Show Raw Blink Samples'}
            </button>
          </div>
        )}
      </div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:8,marginBottom:12}}>
        <h2 style={{marginTop:0}}>Sessions</h2>
        <small className="dim" style={{minWidth:120}}>{status}</small>
      </div>
      <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr style={{background:'#0b1220',color:'#94a3b8'}}>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>Session ID</th>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>Start (UTC)</th>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>End (UTC)</th>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>Total Blinks</th>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>Avg CPU %</th>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>Avg Memory MB</th>
              <th style={{textAlign:'left',padding:10,borderBottom:'1px solid #1f2937'}}>Energy</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r,i)=> (
              <tr key={i} style={{borderBottom:'1px solid #1f2937'}}>
                <td style={{padding:10,fontFamily:'monospace'}}>{r.client_session_id}</td>
                <td style={{padding:10}}>{formatLocal(r.started_at_utc)}</td>
                <td style={{padding:10}}>{formatLocal(r.ended_at_utc)}</td>
                <td style={{padding:10}}>{r.total_blinks ?? ''}</td>
                <td style={{padding:10}}>{r.avg_cpu_percent ?? ''}</td>
                <td style={{padding:10}}>{r.avg_memory_mb ?? ''}</td>
                <td style={{padding:10}}>{r.energy_impact ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showBlinks && (
        <div style={{marginTop:40}}>
          <h2 style={{marginTop:0}}>Recent Blink Samples (latest 150)</h2>
          {blinkSamples.length === 0 && (
            <div className="dim" style={{marginBottom:12,fontSize:13}}>
              No raw blink samples found for this user. Showing synthesized rows from session data.
            </div>
          )}
          <div className="table-wrapper">
            <table className="table" style={{fontSize:12}}>
              <thead>
                <tr style={{background:'#0b1220',color:'#94a3b8'}}>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>Captured (UTC)</th>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>Blink Count</th>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>Device</th>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>App Ver</th>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>CPU%</th>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>Mem MB</th>
                  <th style={{textAlign:'left',padding:8,borderBottom:'1px solid #1f2937'}}>Energy</th>
                </tr>
              </thead>
              <tbody>
                {(blinkSamples.length > 0 ? blinkSamples : rows.slice(0,150).map(r=>({
                  captured_at_utc: r.started_at_utc,
                  blink_count: r.total_blinks,
                  device_id: r.device_id,
                  app_version: r.app_version,
                  cpu_percent: r.avg_cpu_percent,
                  memory_mb: r.avg_memory_mb,
                  energy_impact: r.energy_impact,
                  synthetic: true
                })) ).map((b,i)=>(
                  <tr key={i} style={{borderBottom:'1px solid #1f2937'}}>
                    <td style={{padding:8}}>{formatLocal(b.captured_at_utc)}{b.synthetic ? ' *' : ''}</td>
                    <td style={{padding:8}}>{b.blink_count}</td>
                    <td style={{padding:8}}>{b.device_id}</td>
                    <td style={{padding:8}}>{b.app_version}</td>
                    <td style={{padding:8}}>{b.cpu_percent ?? ''}</td>
                    <td style={{padding:8}}>{b.memory_mb ?? ''}</td>
                    <td style={{padding:8}}>{b.energy_impact ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {blinkSamples.length === 0 && (
            <div className="dim" style={{marginTop:8,fontSize:11}}>* synthesized from session records</div>
          )}
        </div>
      )}
    </main>
  )
}
