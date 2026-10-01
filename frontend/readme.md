

---

```markdown
# ⚡ Troubleshoot AI — Frontend Service

A conversational cloud troubleshooting interface built with **Chainlit**, featuring a **Google Gemini Dark Theme**, ephemeral stateless sessions (optimized for Google Cloud Run and Cloud Workstations), and role-based privilege switching powered by **Google Cloud Identity Platform** and **Vertex AI Agent Engine**.

---

## 📑 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local & Cloud Workstation Setup](#local--cloud-workstation-setup)
- [Running the Application](#running-the-application)
- [Key Features & User Flows](#key-features--user-flows)
  - [1. Standard Diagnostic Mode](#1-standard-diagnostic-mode)
  - [2. Admin Mode & Modal Authentication](#2-admin-mode--modal-authentication)
  - [3. Knowledge Base Ingestion Guard](#3-knowledge-base-ingestion-guard)
  - [4. Real-time Thought & Token Streaming](#4-real-time-thought--token-streaming)
- [Deployment (Google Cloud Run)](#deployment-google-cloud-run)
- [Troubleshooting & Common Fixes](#troubleshooting--common-fixes)

---

## 🏛 Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Browser / Client UI                      │
│   (Gemini Dark UI, Quick Chips, Admin Modal)           │
└──────────────────────────┬─────────────────────────────┘
                           │ WebSockets & SSE
                           ▼
┌────────────────────────────────────────────────────────┐
│            Chainlit Frontend (app.py)                  │
│  - Ephemeral user session management                   │
│  - Event capturing & intent classification             │
└────────────┬─────────────────────────────┬─────────────┘
             │                             │
             │ (Identity Toolkit REST API) │ (Vertex AI Reasoning Engine API)
             ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   GCP Identity Platform  │  │ Vertex AI Agent Engine   │
│  (Admin Authentication)  │  │ (RAG & BQ Vector Search) │
└──────────────────────────┘  └──────────────────────────┘
```

- **Stateless & In-Memory:** Conversation sessions are transient per tab—no sticky database required, making scaling seamless on Cloud Run.
- **Client-Side Event Delegation:** Custom JavaScript intercepts interactive cards and dynamic modal triggers even when HTML is sanitized.
- **Direct GCP Identity Platform Auth:** Admin verification executes securely via Google Application Default Credentials (ADC) / Service Account bearer tokens against Google Identity Toolkit.

---

## 📂 Folder Structure

```
frontend/
├── .chainlit/
│   └── config.toml          # Chainlit configuration (themes, unsafe HTML enabled, origin policy)
├── public/
│   ├── custom.js            # Delegated event listener, Admin modal injection & chat input controller
│   └── style.css            # Gemini dark theme styling, gradient banners, chips, and modal layout
├── .env                     # Local environment secrets and GCP settings (git-ignored)
├── agent_client.py          # Vertex AI Reasoning Engine SSE query & token streaming client
├── app.py                   # Main Chainlit application, lifecycle hooks, and hero layout
├── auth.py                  # Identity Platform authentication via Service Account credentials
├── config.py                # Environment parser and centralized logging setup
├── requirements.txt         # Pinned Python dependencies
├── session_service.py       # Session lifecycle provisioner on Vertex AI Reasoning Engine
└── README.md                # Frontend documentation
```

---

## 📦 Prerequisites

1. **Python 3.10 to 3.12** installed.
2. **Google Cloud SDK (`gcloud`)** installed and authenticated:
   ```bash
   gcloud auth application-default login
   gcloud config set project saas-poc-env
   ```
3. A deployed **Vertex AI Reasoning Engine (Agent Engine)** instance.
4. **Google Cloud Identity Platform** enabled in your GCP project with Email/Password sign-in provider configured.

---

## ⚙️ Environment Configuration

Create or update the `.env` file in the root of `frontend/`:

```env
# Google Cloud Project Details
GCP_PROJECT_ID=saas-poc-env
GCP_LOCATION=us-central1

# Vertex AI Reasoning Engine ID (Required for live agent communication)
ENGINE_ID=YOUR_REASONING_ENGINE_ID

# Optional: Override Reasoning Engine Base URL directly
# VERTEX_AI_AGENT_ENGINE_URL=https://us-central1-aiplatform.googleapis.com/v1/projects/.../reasoningEngines/...

# Logging Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Networking & Cloud Workstation Proxy defaults
CHAINLIT_HOST=0.0.0.0
CHAINLIT_PORT=8501
```

---

## 🚀 Local & Cloud Workstation Setup

### 1. Create and Activate Virtual Environment
```bash
cd frontend
python3 -m venv .frontend
source .frontend/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Verify System Health
Run a quick diagnostic check to verify that all syntax, assets, and imports load cleanly:
```bash
python3 -c '
import py_compile, importlib
modules = ["config", "auth", "session_service", "agent_client", "app"]
for m in modules:
    py_compile.compile(m + ".py", doraise=True)
    importlib.import_module(m)
    print(" [PASS] " + m + ".py")
print("All frontend modules validated successfully.")
'
```

---

## 🖥 Running the Application

### Running on Cloud Workstations / Cloud Shell
When developing in cloud-hosted environments, bind to `0.0.0.0` and run `--headless` to prevent timeout warnings from the cloud web proxy:

```bash
chainlit run app.py --host 0.0.0.0 --port 8501 --headless -w
```

### Running Locally on your Laptop
```bash
chainlit run app.py -w
```

Once running, access the application at `http://localhost:8501` or through the **Cloud Workstation Web Preview** port `8501`.

> **Note:** On your first launch, perform a hard refresh (`Ctrl + Shift + R` or `Cmd + Shift + R`) to ensure your browser does not serve cached CSS/JS assets.

---

## 🌟 Key Features & User Flows

### 1. Standard Diagnostic Mode
- Any user opening a chat session starts in **Standard Mode (Public)** with an ephemeral `guest_<id>`.
- Users can click on pre-built Gemini prompt chips (e.g., *Fix 403 IAM Permission Failure*, *Diagnose Quota Limits*) to auto-populate the prompt.
- RAG diagnostics query BigQuery vector indices through the Reasoning Engine.

### 2. Admin Mode & Modal Authentication
- Clicking **⚡ Switch to ADMIN MODE** triggers a non-intrusive floating dialog.
- Users authenticate against Google Identity Platform using their email and password.
- Upon successful authentication, the session escalates privileges:
  - Top status bar switches to `⚡ ADMIN MODE (Active) (admin@example.com)`.
  - BigQuery ingestion capabilities are unlocked for that tab.

### 3. Knowledge Base Ingestion Guard
- If a guest user attempts to ingest data into BigQuery (e.g., pasting `KB-ALM-...` raw logs), `app.py` blocks the execution before querying the backend.
- The user is prompted with an interactive button to elevate privileges.

### 4. Real-time Thought & Token Streaming
- Reasoning Engine thought processes (such as vector index searches) are streamed into collapsible Chainlit **Thought & Diagnostic Steps**.
- Final responses stream asynchronously token-by-token using Server-Sent Events (SSE).

---

## 🚢 Deployment (Google Cloud Run)

Because this frontend utilizes ephemeral in-memory sessions, it runs seamlessly on serverless platforms like Google Cloud Run.

### Sample `Dockerfile`
Create a `Dockerfile` in `frontend/`:
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    CHAINLIT_HOST=0.0.0.0 \
    CHAINLIT_PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8080", "--headless"]
```

### Build & Deploy to Cloud Run
```bash
# Build the container with Google Cloud Build
gcloud builds submit --tag gcr.io/saas-poc-env/troubleshoot-frontend:latest

# Deploy to Cloud Run
gcloud run deploy troubleshoot-frontend \
    --image gcr.io/saas-poc-env/troubleshoot-frontend:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars GCP_PROJECT_ID=saas-poc-env,GCP_LOCATION=us-central1,ENGINE_ID=YOUR_REASONING_ENGINE_ID
```

---

## 🛠 Troubleshooting & Common Fixes

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **"Unable to forward request to backend / Port 8501"** | Chainlit bound to loopback `127.0.0.1` instead of `0.0.0.0` in Cloud Workstations. | Start Chainlit with `--host 0.0.0.0 --headless`. |
| **"Switch to ADMIN MODE" button does nothing** | Browser cached old JavaScript or inline `onclick` was stripped by Markdown parser. | Ensure `public/custom.js` is up to date and perform a hard refresh (`Ctrl + Shift + R`). |
| **UI renders chips as raw Markdown code block** | HTML was indented by 4 spaces inside `app.py`. | Keep all multiline HTML strings completely left-aligned (0 leading spaces). |
| **DefaultCredentialsError** | Local environment lacks Google Application Default Credentials. | Run `gcloud auth application-default login`. |
| **Session fails with "fallback_session_..."** | `ENGINE_ID` in `.env` is invalid or not yet configured. | Set a valid Reasoning Engine resource ID in `.env`. |
```