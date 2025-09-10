// Admin section layout with conditional minimal view for the login route
'use client'
import '../theme.css'
import { usePathname } from 'next/navigation'

export default function AdminLayout({ children }) {
  const pathname = usePathname()
  const isLogin = pathname === '/admin' || pathname === '/admin/'

  if (isLogin) {
    return children
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <h1>WaW Admin</h1>
          <div className="dim" style={{fontSize:12}}>Monitoring Console</div>
        </div>
        <div style={{marginTop:'auto',fontSize:12}} className="dim">v1.0.0</div>
      </aside>
      <div className="content-area">
        <header className="top-bar">
          <h2 className="top-bar-title">Admin Dashboard</h2>
          <div className="grow" />
        </header>
        <div className="page-wrapper fade-in">
          {children}
        </div>
      </div>
    </div>
  )
}
