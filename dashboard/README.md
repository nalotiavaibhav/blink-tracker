# WaW Dashboard (Next.js)

A lightweight Next.js app to visualize blink data from the WaW backend.

## Dev

- Ensure the backend is running at <http://localhost:8000>
- In another terminal:

```bash
# Windows PowerShell
cd dashboard
npm install
npm run dev
```

Open <http://localhost:3000>, login with any email/password (MVP), and view the dashboard.

## Build and Export (for backend static hosting)

```bash
cd dashboard
npm install
npm run build
```

This creates a static export in `dashboard/out/`. The backend can serve this folder under `/dashboard` in production.

## Backend URL

The login page includes a field to set the backend URL, stored in localStorage (`waw_api`). Defaults to `http://localhost:8000`.

## Auth

On login, the backend returns `access_token`. It’s stored in localStorage as `waw_token` and used for subsequent API calls.
