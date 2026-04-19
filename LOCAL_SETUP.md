# Local Setup Guide — Proviso

> Get Proviso running on your machine in ~30 minutes.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone & Configure](#2-clone--configure)
3. [OCI Credentials](#3-oci-credentials)
4. [Oracle ADB 26ai Setup](#4-oracle-adb-26ai-setup)
5. [Backend (FastAPI)](#5-backend-fastapi)
6. [Frontend (React)](#6-frontend-react)
7. [Run with Docker Compose](#7-run-with-docker-compose)
8. [Oracle APEX Setup](#8-oracle-apex-setup)
9. [Verify Everything Works](#9-verify-everything-works)
10. [Run Tests](#10-run-tests)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| pip | 23+ | bundled with Python |
| Docker Desktop | 4.x+ | for Docker Compose option |
| OCI CLI | 3.x+ | `pip install oci-cli` |
| Terraform | 1.7+ | for infra bootstrap only |

### Install OCI CLI (if not present)

```bash
pip install oci-cli
oci setup config          # interactive wizard — creates ~/.oci/config
oci iam region list       # smoke test
```

---

## 2. Clone & Configure

```bash
git clone https://github.com/iRajesha/Proviso.git
cd Proviso

# Copy env template
cp .env.example .env
```

Open `.env` in your editor and fill in every value — see Section 3 and 4 for what each needs.

Minimum values to set before first run:
- `OCI_COMPARTMENT_ID`, `OCI_CONFIG_PROFILE`, `OCI_GENAI_ENDPOINT`, `OCI_GENAI_MODEL_ID`
- `ADB_DSN_PROVISO`, `ADB_USER_PROVISO`, `ADB_PASSWORD_PROVISO`, `ADB_WALLET_DIR_PROVISO`
- `API_PORT=8000`, `CORS_ORIGINS=http://localhost:5173`

---

## 3. OCI Credentials

### 3a. API Key Authentication

If you haven't already set up an OCI API key:

```bash
# Generate key pair
mkdir -p ~/.oci
openssl genrsa -out ~/.oci/oci_api_key.pem 2048
chmod 600 ~/.oci/oci_api_key.pem
openssl rsa -pubout -in ~/.oci/oci_api_key.pem -out ~/.oci/oci_api_key_public.pem

# Print fingerprint
openssl rsa -pubout -outform DER -in ~/.oci/oci_api_key.pem | openssl md5 -c
```

Then in the OCI Console:
- Go to **Profile → API Keys → Add API Key**
- Upload `~/.oci/oci_api_key_public.pem`
- Copy the fingerprint shown

### 3b. `.env` OCI values

```env
OCI_REGION=us-chicago-1                          # your home region
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxxx  # target compartment
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx          # from Profile → Tenancy
OCI_GENAI_ENDPOINT=https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130
OCI_GENAI_MODEL_ID=cohere.command-r-plus
OCI_CONFIG_FILE=~/.oci/config                     # OCI SDK credential source
OCI_CONFIG_PROFILE=your_oci_profile_name          # profile section inside config file
```

> **Note:** The backend now authenticates OCI GenAI via OCI SDK signing credentials (config file/profile). `OCI_GENAI_API_KEY` is not required for local runs.

### 3c. Verify OCI GenAI access

```bash
oci generative-ai model list \
  --compartment-id <your_compartment_ocid> \
  --region us-chicago-1
```

You should see `cohere.command-r-plus` in the output. If not, request GenAI access in your tenancy.

---

## 4. Oracle ADB 26ai Setup

### 4a. Provision ADB (if not already done)

In the OCI Console → **Oracle Database → Autonomous Database → Create**:
- Workload type: **Transaction Processing** or **JSON**
- Version: **26ai** (select the latest with AI Vector Search)
- Display name: `proviso-adb`
- Admin password: strong password (save it — you'll need it)
- Network: **Private endpoint** (recommended) or Allow secure access

### 4b. Download wallet

```bash
# In OCI Console → your ADB → DB Connection → Download Wallet
# Or via CLI:
oci db autonomous-database generate-wallet \
  --autonomous-database-id <adb_ocid> \
  --password <wallet_password> \
  --file /tmp/proviso_wallet.zip

mkdir -p ~/oracle/wallet
unzip /tmp/proviso_wallet.zip -d ~/oracle/wallet
```

### 4c. `.env` ADB values

```env
ADB_DSN_PROVISO=proviso_high          # from tnsnames.ora in wallet (use _high, _medium, or _low)
ADB_USER_PROVISO=WORKBENCH_USER
ADB_PASSWORD_PROVISO=your_adb_password
ADB_WALLET_DIR_PROVISO=/Users/yourname/oracle/wallet   # absolute path to wallet folder
```

### 4d. Create DB user and run schema

Connect to ADB as ADMIN (use SQL Worksheet in OCI Console or SQLcl):

```sql
-- Create application user
CREATE USER WORKBENCH_USER IDENTIFIED BY "YourSecurePassword_1!";
GRANT CREATE SESSION, CREATE TABLE, CREATE INDEX,
      CREATE TRIGGER, CREATE VIEW TO WORKBENCH_USER;
GRANT UNLIMITED TABLESPACE TO WORKBENCH_USER;

-- Grant vector and context privileges
GRANT EXECUTE ON DBMS_VECTOR TO WORKBENCH_USER;
GRANT EXECUTE ON CTX_DDL TO WORKBENCH_USER;
```

Then run the schema as WORKBENCH_USER:

```bash
# Using SQLcl
sql WORKBENCH_USER/YourPassword@proviso_high \
  -cloudconfig ~/oracle/wallet/Wallet_proviso.zip \
  @backend/db/schema.sql
```

### 4e. Load ONNX embedding model (one-time)

```sql
-- Run as ADMIN — downloads ALL_MINILM_L12_V2 from Oracle Object Storage
BEGIN
  DBMS_VECTOR.LOAD_ONNX_MODEL(
    'ONNX_MODEL_DIR',           -- directory object pointing to your model file
    'all-minilm-l12-v2.onnx',
    'ALL_MINILM_L12_V2',
    JSON('{"function":"embedding","embeddingOutput":"embedding"}')
  );
END;
/
```

> **Shortcut:** If you can't load the ONNX model immediately, the system still works — embeddings will be NULL and vector search will be skipped, falling back to Oracle Text full-text search.

---

## 5. Backend (FastAPI)

### 5a. Verify required backend config

Make sure these values are present in `.env`:

```env
# OCI (required)
OCI_REGION=us-chicago-1
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxxx
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx
OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_PROFILE=your_oci_profile_name
OCI_GENAI_ENDPOINT=https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130
OCI_GENAI_MODEL_ID=cohere.command-r-plus

# ADB (required for persistence/search; generation still works if DB logging is unavailable)
ADB_DSN_PROVISO=proviso_high
ADB_USER_PROVISO=WORKBENCH_USER
ADB_PASSWORD_PROVISO=your_adb_password
ADB_WALLET_DIR_PROVISO=/Users/yourname/oracle/wallet

# App runtime (recommended)
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 5b. Create virtual environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5c. Set PYTHONPATH

```bash
# If you're currently in backend/, move back first
cd ..
source backend/.venv/bin/activate
export PYTHONPATH=$(pwd)
```

### 5d. Start the API server

```bash
# From repo root
uvicorn backend.main:app --reload --port ${API_PORT:-8000}
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 5e. Open API docs

- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc
- Health:      http://localhost:8000/api/v1/health

---

## 6. Frontend (React)

### 6a. Install dependencies

```bash
# From repo root
cd frontend
npm install
```

### 6b. Start frontend dev server

```bash
# From frontend/
npm run dev
```

Frontend URL:
- http://localhost:5173

Notes:
- Frontend uses Vite proxy to call backend at `http://localhost:8000`.
- Keep backend and frontend running in separate terminals.

### 6c. Recommended startup sequence (two terminals)

Terminal 1 (backend):
```bash
cd /path/to/Proviso
source backend/.venv/bin/activate
export PYTHONPATH=$(pwd)
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd /path/to/Proviso/frontend
npm install
npm run dev
```

---

## 7. Run with Docker Compose

If you prefer containers over a local Python install:

```bash
# From repo root
cp .env.example .env   # fill in values first

# Build and start
docker compose up --build

# Or in background
docker compose up -d --build

# Check logs
docker compose logs -f api
```

> **Wallet volume:** Update `ADB_WALLET_DIR_PROVISO` in `.env` to an absolute path on your host.
> Docker Compose mounts it read-only into the container at `/opt/oracle/wallet`.

---

## 8. Oracle APEX Setup

### 8a. Create APEX workspace

In OCI Console → **APEX** → your ADB → **Launch APEX**:
1. Log in as ADMIN
2. Create a new workspace: `PROVISO`
3. Assign it to schema `WORKBENCH_USER`

### 8b. Create a new app

1. **App Builder → Create → New Application**
   - Name: `Proviso`
   - Theme: Universal Theme (42)
2. Create **Page 1** — Generate Infrastructure
3. Create **Page 2** — Gold Script Library

### 8c. Upload static files

**Shared Components → Static Application Files → Upload:**
- `apex/js/proviso.js`
- `apex/css/proviso.css`

Reference them in your page's **JavaScript** and **CSS** sections:
```
#APP_FILES#proviso.js
#APP_FILES#proviso.css
```

### 8d. Add Mermaid.js CDN

In **Shared Components → User Interface Attributes → JavaScript → File URLs**:
```
https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js
```

### 8e. Register AJAX callbacks

For each page, go to **Processing** tab and add an **AJAX Callback** process. 
Copy the PL/SQL from `apex/plsql_callbacks.sql` — one process per block:

| Process Name | Page | PL/SQL Block |
|---|---|---|
| `GENERATE_INFRA` | 1 | Block 1 from `plsql_callbacks.sql` |
| `SAVE_SCRIPT` | 1 | Block 2 |
| `SEARCH_SCRIPTS` | 2 | Block 3 |
| `GET_SCRIPT` | 2 | Block 4 |

### 8f. Update API base URL

In `plsql_callbacks.sql` the API URL defaults to `http://localhost:8000`.  
If your FastAPI runs on a different host/port, do a find-replace before pasting into APEX.

---

## 9. Verify Everything Works

```bash
# 1. Backend health check
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok","version":"1.0.0"}

# 2. Create chat session
curl -s -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"services":["Networking","Compute"]}' \
  | python -m json.tool

# Copy session_id from output, then:
SESSION_ID=<paste_session_id_here>

# 3. Generate Terraform draft (generator only)
curl -s -X POST http://localhost:8000/api/v1/chat/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Create a production setup in ap-hyderabad-1 with private subnet and one compute instance. Allow SSH from 10.10.0.0/24 only.",
    "intent":"generate"
  }' \
  | python -m json.tool

# 4. Run review explicitly (reviewer agent)
curl -s -X POST http://localhost:8000/api/v1/chat/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message":"","intent":"review"}' \
  | python -m json.tool

# 5. Run cleanup explicitly (cleanup agent)
curl -s -X POST http://localhost:8000/api/v1/chat/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message":"","intent":"cleanup"}' \
  | python -m json.tool

# 6. Diff endpoint smoke test
curl -s -X POST http://localhost:8000/api/v1/review/diff \
  -H "Content-Type: application/json" \
  -d '{"original":"resource \"oci_core_vcn\" \"main\" {}","modified":"resource \"oci_core_vcn\" \"main\" {\n  cidr_block = \"10.0.0.0/16\"\n}"}' \
  | python -m json.tool
```

Frontend check:
- Open `http://localhost:5173`
- Confirm chat loads a session id and buttons:
  - `Generate Draft`
  - `Run Review`
  - `Generate Cleanup`

---

## 10. Run Tests

```bash
# Backend tests (from repo root with backend venv active)
export PYTHONPATH=$(pwd)
cd backend
pytest tests/ -v
```

Expected output:
```
tests/test_health.py::test_health              PASSED
tests/test_diagram.py::test_empty_services_returns_default  PASSED
tests/test_diagram.py::test_compute_and_adb    PASSED
tests/test_diagram.py::test_full_stack         PASSED
tests/test_diff_service.py::test_unified_diff_detects_changes  PASSED
tests/test_diff_service.py::test_no_diff_for_identical  PASSED
```

> Tests that call CrewAI (`test_generate_route.py`) are mocked and don't require OCI access.

```bash
# Frontend build check
cd ../frontend
npm run build
```

---

## 11. Troubleshooting

### `ModuleNotFoundError: No module named 'backend'`
```bash
# Ensure you're in repo root, not backend/
export PYTHONPATH=$(pwd)
uvicorn backend.main:app --reload
```

### `oracledb.DatabaseError: ORA-01017` (wrong password)
- Double-check `ADB_PASSWORD_PROVISO` in `.env`
- Ensure `ADB_USER_PROVISO` matches the DB user you created

### `oracledb.DatabaseError: DPY-4011` (wallet not found)
- Set `ADB_WALLET_DIR_PROVISO` to absolute path (no `~`)
- Ensure `sqlnet.ora` and `tnsnames.ora` exist in that directory

### OCI GenAI call errors
- Confirm OCI GenAI service is available in your region: `us-chicago-1` or `eu-frankfurt-1`
- Check `~/.oci/config` has the profile named in `.env` as `OCI_CONFIG_PROFILE`
- Verify the model ID: `cohere.command-r-plus` (exact string)
- Ensure `OCI_COMPARTMENT_ID` is set in `.env`

### Frontend cannot call backend (`Failed to fetch` / network error)
- Make sure backend is running on `http://localhost:8000`
- Make sure frontend is running via Vite (`npm run dev` in `frontend/`)
- If you changed backend port, update `frontend/vite.config.js` proxy target

### Generation timeout in APEX (30s limit)
- Increase APEX Ajax timeout: in the AJAX Callback process, add to the `apex.server.process` call:
  ```javascript
  { timeout: 120000 }   // 120 seconds
  ```
- Or switch to async polling (see AGENT.md for the async pattern)

### Docker: wallet mount fails
```yaml
# In docker-compose.yml, use explicit absolute path:
volumes:
  - /Users/yourname/oracle/wallet:/opt/oracle/wallet:ro
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `uvicorn backend.main:app --reload` | Start API (dev) |
| `cd frontend && npm run dev` | Start React frontend |
| `docker compose up --build` | Start via Docker |
| `pytest tests/ -v` | Run test suite |
| `curl localhost:8000/api/v1/health` | Health check |
| `terraform -chdir=terraform init` | Init Terraform |
| `terraform -chdir=terraform plan` | Preview infra changes |
