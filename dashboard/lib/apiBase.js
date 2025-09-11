// Centralized API base URL resolution for the dashboard
// Order of precedence:
// 1) NEXT_PUBLIC_API_BASE (set on Vercel or at build time)
// 2) window.location.origin (works when dashboard is served by the backend at /dashboard)
// 3) http://localhost:8000 (dev fallback)
export function getApiBase() {
  // 1) Environment variable takes precedence (set on Render)
  if (process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.trim()) {
    return process.env.NEXT_PUBLIC_API_BASE.trim().replace(/\/$/, '');
  }
  
  // 2) Production default - point to your deployed backend
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    const origin = window.location.origin.replace(/\/$/, '');
    // If we're on localhost dev, use local backend
    if (/^http:\/\/localhost:3000$/.test(origin) || /^http:\/\/127\.0\.0\.1:3000$/.test(origin)) {
      return 'http://127.0.0.1:8000';
    }
    // For production deployment, use your deployed backend
    if (origin.includes('render.com') || origin.includes('onrender.com')) {
      return 'https://waw-backend-a28q.onrender.com';
    }
    return origin;
  }
  
  // 3) Final fallback - deployed backend
  return 'https://waw-backend-a28q.onrender.com';
}
