# Dashboard Deployment Guide

## Deploying to Render

1. **Push to GitHub**: Ensure your dashboard code is in your repository
2. **Create Web Service**: 
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `dashboard` directory as the root directory
3. **Configure Service**:
   - **Name**: `waw-dashboard`
   - **Environment**: `Node`
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your preferred branch)
   - **Root Directory**: `dashboard`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`

## Environment Variables

Set these in Render dashboard:
- `NODE_ENV`: `production`
- `NEXT_PUBLIC_API_BASE`: `https://waw-backend-a28q.onrender.com`

## Alternative: Manual Deployment

If you prefer to deploy manually:

```bash
cd dashboard
npm install
npm run build
npm start
```

## Local Development

```bash
cd dashboard
npm install
npm run dev
```

Access at: http://localhost:3000
