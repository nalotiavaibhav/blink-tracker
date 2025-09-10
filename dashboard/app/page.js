export const dynamic = 'force-static'

export default function HomeRedirect() {
  return (
    <main style={{display:'grid',placeItems:'center',minHeight:'100vh',background:'#0f172a',color:'#e5e7eb',fontFamily:'system-ui,sans-serif'}}>
      <div style={{textAlign:'center'}}>
        <h1 style={{marginTop:0}}>Admin Dashboard</h1>
        <p style={{color:'#94a3b8'}}>This interface is restricted to authorized administrators.</p>
        <a href="/admin" style={{display:'inline-block',marginTop:12,padding:'10px 18px',background:'#2563eb',color:'#fff',borderRadius:8,textDecoration:'none',fontWeight:600}}>Go to Admin Login</a>
      </div>
    </main>
  )
}
