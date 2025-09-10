'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getApiBase } from '../../lib/apiBase'

export default function DashboardPage(){
  const [summary, setSummary] = useState(null)
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('')
  const router = useRouter()

  const backendBase = getApiBase()
  const token = typeof window !== 'undefined' ? localStorage.getItem('waw_token') : ''

  async function api(path){
    const res = await fetch(`${backendBase}${path}`, { headers: { 'Authorization': `Bearer ${token}` } })
    if(!res.ok) throw new Error('request failed')
    return res.json()
  }

  async function load(){
    try{
      setStatus('Loading…')
      const [s, list] = await Promise.all([
        api('/v1/sessions/summary'),
        api('/v1/sessions?limit=100')
      ])
      setSummary(s)
      setRows(Array.isArray(list) ? list : (list.items || []))
      setStatus('')
    }catch(e){
      setStatus('Failed to load. Are you logged in?')
    }
  }

  useEffect(()=>{
    if(!token){ router.replace('/'); return }
    load()
    const id = setInterval(load, 15000)
    return ()=>clearInterval(id)
  },[])

  return (
    <main style={{padding:24,background:'#0f172a',minHeight:'100vh',color:'#e5e7eb'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <h1 style={{marginTop:0}}>Blink Dashboard</h1>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <button onClick={()=>router.push('/')} style={{padding:8,borderRadius:6,border:'1px solid #1f2937',background:'#111827',color:'#e5e7eb'}}>Logout</button>
          <small style={{color:'#94a3b8'}}>{status}</small>
        </div>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,margin:'12px 0'}}>
        <Card label="Total Blinks" value={summary?.total_blinks ?? 0} />
        <Card label="Total Sessions" value={summary?.total_sessions ?? 0} />
        <Card label="Avg CPU %" value={(summary?.average_cpu_percent ?? 0).toFixed(2)} />
        <Card label="Avg Memory (MB)" value={(summary?.average_memory_mb ?? 0).toFixed(0)} />
      </div>
      <div style={{overflow:'auto',background:'#111827',border:'1px solid #1f2937',borderRadius:12}}>
        <table style={{width:'100%',borderCollapse:'collapse'}}>
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
                <td style={{padding:10}}>{String(r.started_at_utc).replace('T',' ').replace('Z','')}</td>
                <td style={{padding:10}}>{String(r.ended_at_utc).replace('T',' ').replace('Z','')}</td>
                <td style={{padding:10}}>{r.total_blinks ?? ''}</td>
                <td style={{padding:10}}>{r.avg_cpu_percent ?? ''}</td>
                <td style={{padding:10}}>{r.avg_memory_mb ?? ''}</td>
                <td style={{padding:10}}>{r.energy_impact ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}

function Card({label, value}){
  return (
    <div style={{background:'#111827',border:'1px solid #1f2937',borderRadius:12,padding:14}}>
      <div style={{color:'#94a3b8',fontSize:12}}>{label}</div>
      <div style={{marginTop:6,fontSize:24,fontWeight:700}}>{value}</div>
    </div>
  )
}
