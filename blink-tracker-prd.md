# 📄 Product Requirements Document (PRD)  

**Project:** Wellness at Work (WaW) – Cloud-Synced Eye Blink Tracker

**Date:** 20th August 2025

**Version:** 1.0

---

## 1. Executive Summary

The **Wellness at Work Eye Tracker** is a cross-platform desktop application designed to monitor eye blinks in real-time, sync user wellness data securely to the cloud, and visualize this data on a web-based dashboard.  
The product supports **Windows and macOS** laptops, complies with **GDPR** for data protection, and provides insights into digital eye strain and user wellness.  

---

## 2. Problem Statement

- Millions of professionals spend hours in front of screens, leading to digital eye strain and reduced productivity.  
- Existing solutions for eye wellness are fragmented and not integrated across devices.  
- WaW seeks to build a **cross-platform, privacy-first, end-to-end system** that measures blink activity, syncs data, and visualizes it for user awareness.  

---

## 3. Objectives & Goals

- Deliver a **desktop application** that monitors blink activity and system resource usage.  
- Enable **cloud-based syncing** for portability and long-term tracking.  
- Provide a **read-only dashboard** for users to visualize blink history and wellness patterns.  
- Ensure **GDPR compliance** by integrating consent flows, data minimization, and deletion policies.  
- Showcase a **scalable architecture** that can extend into production-ready deployment.  

---

## 4. Scope of Work

### In-Scope

1. **Desktop Application (PyQt, cross-platform)**  
   - Login and user authentication.  
   - Real-time blink tracking (via provided Python eye-tracker).  
   - Performance monitoring (CPU %, memory MB, energy impact).  
   - Offline data capture with sync-on-reconnect.  
   - Minimalist grayscale UI (black/white/grey).  

2. **Backend & Database (AWS + FastAPI)**  
   - Database schema for users and blink data.  
   - Secure APIs to receive, store, and expose data.  
   - AWS deployment (RDS for relational DB, S3 for storage).  
   - Offline-first support: idempotent batch uploads.  

3. **Web Dashboard (Next.js)**  
   - Read-only user login.  
   - Visualization of blink patterns (charts + tables).  
   - Secure fetch from backend APIs.  

4. **Documentation & Compliance**  
   - GDPR explanation in README (what’s implemented now, what will be added later).  
   - Security considerations documented.  
   - CI/CD pipeline with sample test cases.  
   - Installer packaging for Windows/macOS.  

### Out-of-Scope (Optional / Future Work)

- Notifications when blink count is too low.  
- System tray (Windows) / Menu bar (macOS) integration.  
- C++ rewrite of blink detection logic.  
- Microservice decomposition of backend.  
- Advanced cross-hardware testing methodology.  

---

## 5. Users & Use Cases

### Target Users

- **Primary:** Office workers, students, professionals spending >6 hrs/day on laptops.  
- **Secondary:** Organizations monitoring workplace wellness trends.  

### Key Use Cases

1. A user logs into the desktop app, starts work, and sees their blink count updated in real-time.  
2. The app monitors blinks offline (on a train, café without Wi-Fi) and syncs later when online.  
3. The backend securely stores user data in AWS RDS.  
4. The user logs into the WaW web dashboard and visualizes their blink history.  
5. An administrator exports aggregated blink data (future org-level insights).  

---

## 6. Functional Requirements

### 6.1 Desktop Application

- **Login:** User authentication.  
- **Blink Tracking:** Integration with Python eye-tracker; real-time blink count display.  
- **Performance Metrics:** CPU %, memory MB, energy impact.  
- **Offline Mode:** Local SQLite storage, retries on reconnect.  
- **UI:** PyQt6 app with grayscale theme.  

### 6.2 Backend & Database

- **API Endpoints:**  
  - `GET /v1/me` → user profile.  
  - `POST /v1/blinks` → batch upload blink samples.  
  - `GET /v1/blinks` → fetch blink data (date-filtered).  
- **Database Schema:**  
  - Users: `id, email, name, consent, created_at`.  
  - BlinkSamples: `id, user_id, client_sequence, captured_at_utc, blink_count, device_id, app_version`.  
- **AWS Infrastructure:**  
  - RDS (Postgres).  
  - S3 (backup/logs).  
  - ECS or Elastic Beanstalk for deployment.  
- **Security:** JWT authentication, HTTPS everywhere, encryption at rest.  

### 6.3 Web Dashboard

- **Login:** User login with JWT session.  
- **Dashboard:** Show blink counts, charts, and summaries.  
- **Filters:** Date range picker (daily/weekly).  
- **Read-Only:** No data modification, only visualization.  

---

## 7. Non-Functional Requirements

- **Cross-platform:** Windows + macOS desktop builds.  
- **Performance:**  
  - Desktop app should run with <10% CPU overhead.  
  - Sync should tolerate intermittent connectivity.  
- **Security & GDPR:**  
  - Explicit consent required before collecting data.  
  - Right to erasure supported.  
  - Encrypted data transfer.  
- **Scalability:** Backend must support thousands of users with minimal changes.  
- **Reliability:** Offline-first design with queueing + retries.  

---

## 8. Deliverables

- **Source Code:** Desktop app, backend, web app (GitHub).  
- **README.md:** Architecture diagram, GDPR/Security explanation, sample CI test cases.  
- **CI/CD:** GitHub Actions pipelines (linting, testing, builds).  
- **Distributions:**  
  - Windows `.exe` / MSIX installer.  
  - macOS `.app` / `.dmg` (TestFlight preferred).  
- **Test Invitations:** Email builds to `ishaan80@gmail.com` and `mehul.bhardwaj@outlook.com`.  

---

## 9. Success Metrics

- ✅ **Functionality:** Blink detected on desktop → synced → visible in web dashboard.  
- ✅ **Compliance:** GDPR considerations documented.  
- ✅ **Distribution:** At least one OS installer working end-to-end.  
- ✅ **CI/CD:** Basic test automation running on GitHub.  
- ✅ **Documentation:** Clear architecture and future roadmap.  

---

## 10. Risks & Mitigations

- **Packaging difficulty (macOS notarization)** → Provide `.dmg` + document TestFlight as future plan.  
- **Eye-tracker integration issues** → Stub blink count with mock generator until real integration is stable.  
- **Time constraints** → Deliver MVP (core flow working) and document optional items.  
- **GDPR compliance gaps** → Document planned steps for production readiness.  

---

## 11. Timeline (1 Week, 8–9 hrs/day)

- **Day 1–2:** Backend schema + FastAPI endpoints (local SQLite).  
- **Day 3–4:** PyQt desktop MVP (login, blink counter, perf stats, offline sync).  
- **Day 5:** Web dashboard MVP (Next.js, fetch + chart).  
- **Day 6:** Packaging desktop app + CI/CD setup.  
- **Day 7:** Documentation polish, architecture diagram, test final flow.  

---
