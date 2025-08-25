🏗️ Architecture Overview

The Wellness at Work (WaW) system consists of three main components:

Desktop Application (PyQt)

Tracks real-time eye blinks using the provided Python eye-tracker.

Collects performance metrics (CPU %, memory usage, energy impact).

Stores data locally in SQLite when offline and syncs to the backend once reconnected.

Backend Service (FastAPI on AWS)

Exposes secure REST APIs (/me, /blinks) for ingesting and retrieving user data.

Manages authentication via JWT and enforces GDPR principles such as consent gating.

Persists data in AWS RDS (PostgreSQL); SQLite is used in local development.

Stores backups/logs in AWS S3 for durability.

Web Dashboard (Next.js)

Provides a read-only visualization of user blink history and wellness insights.

Fetches blink data securely from the backend.

Displays results in interactive charts and tables.

🔗 Data Flow

The Desktop App captures blink samples and performance stats → sends them to the Backend APIs via HTTPS.

The Backend writes data into the Database (RDS/SQLite) and optionally archives to S3.

The Web Dashboard fetches the data securely and presents it to the user.