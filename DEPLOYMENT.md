# Deployment Guide

This guide explains how to deploy the WaW backend (FastAPI) and the dashboard (Next.js) with minimal steps.

## 1) Prerequisites

- A server or PaaS for the backend (VM, Render, Fly.io, Azure App Service, etc.).
- A Postgres database (AWS RDS recommended) or keep SQLite for demos.
- A static host or Vercel/Netlify for the dashboard.
- Domain(s) and HTTPS (recommended).

## 2) Environment variables

Create a `.env` next to the backend with at least:

- DATABASE_URL=postgresql://USER:PASS@HOST:5432/DBNAME?sslmode=require
- JWT_SECRET_KEY=your-strong-key
- ADMIN_EMAILS="admin@example.com,another@org.com"
- ADMIN_API_KEY=your-random-admin-key
- CORS_ORIGINS=["https://dashboard.example.com","http://localhost:3000"]
- GOOGLE_CLIENT_ID=your-desktop-oauth-client-id

Optional: API_HOST, API_PORT, LOG_LEVEL, etc. See `.env.example`.

## 3) Backend deploy

- Install Python 3.10+ and dependencies: `pip install -r requirements.txt`.
- Set env vars above in your service.
- Run the app (example): `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
- Put it behind a reverse proxy (Nginx) and enable HTTPS.

Health endpoints (for container orchestrators):

- Liveness: `GET /health/liveness`
- Readiness: `GET /health/readiness` (verifies initial DB connectivity)
- General: `GET /health`

If readiness returns 503, the process is up but DB was unreachable at startup; it will auto re-check on subsequent readiness probes.

Notes:

- The backend will mount a static dashboard at `/dashboard` if `dashboard/out` exists on the server.
- CORS is now driven via `CORS_ORIGINS` env var.

## 4) Dashboard deploy

Two options:

A) Static export (simple hosting)

- In `dashboard/`, set NEXT_PUBLIC_API_BASE to your backend URL (e.g., <https://api.example.com>).
  - On Vercel/Netlify, add env var `NEXT_PUBLIC_API_BASE`.
- Build: `npm ci && npm run build` (this runs `next build && next export`).
- Host the generated `dashboard/out` on any static host, or copy it to the backend server and the API will serve it at `/dashboard`.

B) Server-rendered (Next start)

- Build: `npm ci && npm run build` (remove `next export` if SSR is needed).
- Start: `npm run start` behind a Node process manager.
- Ensure `NEXT_PUBLIC_API_BASE` points to the backend.

## 5) Admin access

- Use either an admin-scoped JWT (email in ADMIN_EMAILS) or send header `X-Admin-Key: <ADMIN_API_KEY>`.
- Admin pages live under `/admin` in the dashboard.

## 6) Smoke test

- Open API docs: <https://api.example.com/docs>
- Login on dashboard: <https://dashboard.example.com>
- Verify sessions table populates and admin pages load with your admin account.

## 7) Troubleshooting

- 401 on admin pages: ensure your email is in ADMIN_EMAILS or send X-Admin-Key.
- CORS blocked: set CORS_ORIGINS to include your dashboard origin exactly (scheme + host + port).
- Google login failing: verify GOOGLE_CLIENT_ID matches the client that issued the ID token.
- SQLite lock issues: migrate to Postgres for multi-user prod.

## 8) Production docker-compose example

An opinionated example combining Postgres, API, and dashboard is provided in `docker-compose.production.yml`.

Usage (adjust secrets first):

```bash
docker compose -f docker-compose.production.yml up -d --build
```

Then visit:

- API docs: <http://localhost:8000/docs>
- Dashboard: <http://localhost:3000>

IMPORTANT: Replace default passwords, set a strong `JWT_SECRET_KEY`, and consider enabling HTTPS via a reverse proxy (Caddy / Traefik / Nginx) in front of these services.
