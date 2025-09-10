# WaW Backend Deployment (RDS + Persistent Server)

This doc shows two reliable ways to run the FastAPI backend against AWS RDS without relying on your local machine.

Prereqs:
- AWS RDS Postgres running and reachable from your server or container.
- A VM (Ubuntu) or a container platform (ECS/Fargate/Docker host).
- Your .env secrets ready (DATABASE_URL, JWT_SECRET_KEY, SMTP_*, etc.).

Option A) Docker (single container)
1) Build image
   docker build -t waw-backend:latest .
2) Run container (replace values)
   docker run -d --name waw-backend -p 8000:8000 \
     -e DATABASE_URL="postgresql://USER:PASS@HOST:5432/DBNAME" \
     -e JWT_SECRET_KEY="your-strong-secret" \
     -e CORS_ORIGINS='["https://dashboard.example.com","http://localhost:3000"]' \
     -e SMTP_HOST=smtp.gmail.com -e SMTP_PORT=587 -e SMTP_USER=you@gmail.com -e SMTP_PASSWORD=app-pass -e SMTP_FROM="WAW <you@gmail.com>" \
     waw-backend:latest
3) Verify
   curl http://SERVER_IP:8000/health

Notes:
- Pin your image in ECS or Docker and set env vars via task definition or secrets manager.
- Add an Nginx/ALB with TLS in front of port 8000 in production.

Option B) systemd on a VM
1) Provision VM and install Python 3.11
2) Copy repo to /opt/waw and create venv
   cd /opt/waw
   python3.11 -m venv venv
   source venv/bin/activate && pip install -r requirements.txt
3) Set env in the unit file
   Edit deploy/waw-backend.service with your DATABASE_URL and other secrets
4) Install the unit
   sudo cp deploy/waw-backend.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable waw-backend
   sudo systemctl start waw-backend
5) Verify
   curl http://SERVER_IP:8000/health

RDS specifics
- Use the full Postgres URL (postgresql://USER:PASS@HOST:5432/DBNAME). If SSL required, add ?sslmode=require
- Ensure the VM/container can reach RDS (security group inbound rules and outbound egress).
- Our SQLAlchemy engine uses pool_pre_ping and pool_recycle for RDS idle recovery.

Dashboard
- Set NEXT_PUBLIC_API_BASE to your backend URL and redeploy.

CORS
- Set CORS_ORIGINS to exactly match your dashboard origin(s).

SMTP
- Set SMTP_* env vars so real OTP emails are delivered.

Admin
- Use ADMIN_EMAILS or X-Admin-Key header (ADMIN_API_KEY) for admin endpoints.

Troubleshooting
- 401 on set-password from desktop: ensure the Authorization header with Bearer <token> is sent (desktop fixed). Also verify JWT_SECRET_KEY is consistent across instances.
- Connection refused: open port 8000 on the VM firewall or run behind a reverse proxy and expose 443.
- RDS timeouts: verify security groups and that pool_pre_ping is enabled (it is by default).

Option A2) Docker Compose (recommended)

1) Create a file named `.env.docker` next to `docker-compose.yml` with these keys:
   DATABASE_URL=postgresql://USER:PASS@HOST:5432/DBNAME
   JWT_SECRET_KEY=your-strong-secret
   CORS_ORIGINS=["https://dashboard.example.com","http://localhost:3000"]
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=you@gmail.com
   SMTP_PASSWORD=app-pass
   SMTP_FROM=WAW <you@gmail.com>
 
2) Build and start
   docker compose up -d --build

3) Check health
   curl <http://localhost:8000/health>

Notes (Windows PowerShell)

- Use double quotes for values with spaces when using `docker run`; with Compose, keep JSON arrays (CORS_ORIGINS) as plain JSON in the `.env.docker` file.
- The image installs `requirements.backend.txt` to keep it slim and avoid desktop-only packages.
- `.dockerignore` prevents large/dev files from bloating the image and excludes your local `.env`.
