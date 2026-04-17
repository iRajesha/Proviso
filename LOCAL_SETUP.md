# Local Setup Guide — Proviso

> Get Proviso running on your machine in ~30 minutes.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone & Configure](#2-clone--configure)
3. [OCI Credentials](#3-oci-credentials)
4. [Oracle ADB 26ai Setup](#4-oracle-adb-26ai-setup)
5. [Backend (FastAPI)](#5-backend-fastapi)
6. [Run with Docker Compose](#6-run-with-docker-compose)
7. [Oracle APEX Setup](#7-oracle-apex-setup)
8. [Verify Everything Works](#8-verify-everything-works)
9. [Run Tests](#9-run-tests)
10. [Troubleshooting](#10-troubleshooting)

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
OCI_GENAI_API_KEY=your_api_key_here              # not used directly; SDK reads ~/.oci/config
```

> **Note:** The OCI Python SDK reads `~/.oci/config` automatically when running locally. `OCI_GENAI_API_KEY` is only needed for cloud deployments without instance principal.

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
ADB_DSN=proviso_high          # from tnsnames.ora in wallet (use _high, _medium, or _low)
ADB_USER=WORKBENCH_USER
ADB_PASSWORD=your_adb_password
ADB_WALLET_DIR=/Users/yourname/oracle/wallet   # absolute path to wallet folder
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

### 5a. Create virtual environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5b. Set PYTHONPATH

```bash
# From the repo root (not backend/)
export PYTHONPATH=$(pwd)
```

### 5c. Start the API server

```bash
# From repo root
uvicorn backend.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 5d. Open API docs

- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc
- Health:      http://localhost:8000/api/v1/health

---

## 6. Run with Docker Compose

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

> **Wallet volume:** Update `ADB_WALLET_DIR` in `.env` to an absolute path on your host.
> Docker Compose mounts it read-only into the container at `/opt/oracle/wallet`.

---

## 7. Oracle APEX Setup

### 7a. Create APEX workspace

In OCI Console → **APEX** → your ADB → **Launch APEX**:
1. Log in as ADMIN
2. Create a new workspace: `PROVISO`
3. Assign it to schema `WORKBENCH_USER`

### 7b. Create a new app

1. **App Builder → Create → New Application**
   - Name: `Proviso`
   - Theme: Universal Theme (42)
2. Create **Page 1** — Generate Infrastructure
3. Create **Page 2** — Gold Script Library

### 7c. Upload static files

**Shared Components → Static Application Files → Upload:**
- `apex/js/proviso.js`
- `apex/css/proviso.css`

Reference them in your page's **JavaScript** and **CSS** sections:
```
#APP_FILES#proviso.js
#APP_FILES#proviso.css
```

### 7d. Add Mermaid.js CDN

In **Shared Components → User Interface Attributes → JavaScript → File URLs**:
```
https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js
```

### 7e. Register AJAX callbacks

For each page, go to **Processing** tab and add an **AJAX Callback** process. 
Copy the PL/SQL from `apex/plsql_callbacks.sql` — one process per block:

| Process Name | Page | PL/SQL Block |
|---|---|---|
| `GENERATE_INFRA` | 1 | Block 1 from `plsql_callbacks.sql` |
| `SAVE_SCRIPT` | 1 | Block 2 |
| `SEARCH_SCRIPTS` | 2 | Block 3 |
| `GET_SCRIPT` | 2 | Block 4 |

### 7f. Update API base URL

In `plsql_callbacks.sql` the API URL defaults to `http://localhost:8000`.  
If your FastAPI runs on a different host/port, do a find-replace before pasting into APEX.

---

## 8. Verify Everything Works

```bash
# 1. Health check
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok","version":"1.0.0"}

# 2. Generate Terraform (requires OCI GenAI access)
curl -s -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"requirements":"Create a VCN with two subnets and an ADB","services":["vcn","adb"]}' \
  | python -m json.tool

# 3. Diagram only (no LLM needed)
curl -s -X POST http://localhost:8000/api/v1/review/diff \
  -H "Content-Type: application/json" \
  -d '{"original":"resource \"oci_core_vcn\" \"main\" {}","modified":"resource \"oci_core_vcn\" \"main\" {\n  cidr_block = \"10.0.0.0/16\"\n}"}' \
  | python -m json.tool
```

---

## 9. Run Tests

```bash
# From repo root with venv active
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

---

## 10. Troubleshooting

### `ModuleNotFoundError: No module named 'backend'`
```bash
# Ensure you're in repo root, not backend/
export PYTHONPATH=$(pwd)
uvicorn backend.main:app --reload
```

### `oracledb.DatabaseError: ORA-01017` (wrong password)
- Double-check `ADB_PASSWORD` in `.env`
- Ensure `ADB_USER` matches the DB user you created

### `oracledb.DatabaseError: DPY-4011` (wallet not found)
- Set `ADB_WALLET_DIR` to absolute path (no `~`)
- Ensure `sqlnet.ora` and `tnsnames.ora` exist in that directory

### `LLMResponseError` / `litellm` errors
- Confirm OCI GenAI service is available in your region: `us-chicago-1` or `eu-frankfurt-1`
- Check `~/.oci/config` has correct `[DEFAULT]` profile
- Verify the model ID: `cohere.command-r-plus` (exact string)

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
| `docker compose up --build` | Start via Docker |
| `pytest tests/ -v` | Run test suite |
| `curl localhost:8000/api/v1/health` | Health check |
| `terraform -chdir=terraform init` | Init Terraform |
| `terraform -chdir=terraform plan` | Preview infra changes |
