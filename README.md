# Proviso

> **Describe your OCI infrastructure in plain English. Get production-grade Terraform, security-reviewed and ready to run.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![CrewAI](https://img.shields.io/badge/CrewAI-%3E%3D0.80-orange)](https://www.crewai.com/)
[![OCI GenAI](https://img.shields.io/badge/OCI%20GenAI-Cohere%20Command%20R%2B-red?logo=oracle&logoColor=white)](https://www.oracle.com/artificial-intelligence/generative-ai/)
[![Oracle APEX](https://img.shields.io/badge/Oracle%20APEX-24.1%2B-F80000?logo=oracle&logoColor=white)](https://apex.oracle.com/)
[![ADB 26ai](https://img.shields.io/badge/ADB-26ai-F80000?logo=oracle&logoColor=white)](https://www.oracle.com/autonomous-database/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Proviso is an AI-powered workbench that converts natural-language OCI infrastructure requirements into production-grade Terraform scripts — complete with CIS OCI security review and rollback scripts, all in one pipeline.  
No templates, no stubs. Real `oci_*` resources, real compliance checks, ready to `terraform apply`.

---

## Table of Contents

- [What Is Proviso?](#what-is-proviso)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Why ADB 26ai?](#why-adb-26ai)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [OCI IAM Policies](#oci-iam-policies)
- [Docker Deployment](#docker-deployment)
- [Database Setup](#database-setup)
- [API Reference](#api-reference)
- [Demo Flow](#demo-flow)
- [Sprint Plan](#sprint-plan)
- [Risk Register](#risk-register)
- [See Also](#see-also)
- [License](#license)

---

## What Is Proviso?

Proviso is an AI-powered workbench that converts natural language OCI infrastructure requirements into **production-grade Terraform scripts** through a 3-agent CrewAI pipeline:

1. **Generator Agent** — Turns your description into real `oci_*` Terraform resources
2. **Reviewer Agent** — Audits the output against the CIS OCI Benchmark and rewrites non-compliant sections
3. **Cleanup Agent** — Auto-generates a rollback/destroy script for every provisioning run

Built entirely on the Oracle stack:
- **OCI GenAI** (Cohere Command R+) — LLM for code generation and security review
- **ADB 26ai** — Stores scripts, embeddings, and serves hybrid vector + full-text search
- **Oracle APEX** — Frontend UI with Monaco Editor and Mermaid diagrams
- **OCI API Gateway** — Rate limiting, CORS, and request routing

---

## Key Features

| # | Feature | Description |
|---|---------|-------------|
| **UC1** | 🏗 Natural Language → Terraform | Describe what you need in plain English; get real `oci_*` HCL — not templates, not pseudo-code |
| **UC2** | 🔍 Multi-Agent Security Review | Agent 1 generates, Agent 2 reviews against CIS OCI Benchmark; side-by-side Monaco diff shows every change |
| **UC3** | 🛡 Compliance Guardrails | Agent 2 enforces CIS OCI checks automatically: NSGs, encryption, private endpoints, IAM least-privilege |
| **UC4** | 🔄 Auto-generated Cleanup Scripts | Every provisioning run produces a paired rollback/destroy script for safe teardown |
| **UC5** | 📚 Gold Standard Library | Save reviewed scripts with keywords; search the library via ADB 26ai hybrid vector + full-text search or plain-English Select AI |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         OCI Region                               │
│                                                                  │
│  ┌────────────┐     ┌───────────────┐     ┌──────────────────┐  │
│  │ Oracle APEX │────▶│ OCI API       │────▶│ FastAPI Server   │  │
│  │ (Frontend)  │     │ Gateway       │     │ (Python 3.11+)   │  │
│  │ Public LB   │     │ /api/v1/*     │     │ OCI Compute /    │  │
│  └────────────┘     └───────────────┘     │ Container Inst.  │  │
│                                            └────────┬─────────┘  │
│                                    ┌────────────────┼──────────┐ │
│                                    ▼                ▼          │ │
│                          ┌──────────────┐   ┌──────────────┐  │ │
│                          │ OCI GenAI    │   │ ADB 26ai     │  │ │
│                          │ Cohere       │   │ + Vector     │  │ │
│                          │ Command R+   │   │   Search     │  │ │
│                          └──────────────┘   └──────────────┘  │ │
│                                                               │ │
│  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  Agent 1: Generator ──▶ Agent 2: Reviewer ──▶ Agent 3: Cleanup │  │
│  └─────────────────────────────────────────────────────────┘  │ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI Agents | CrewAI >=0.80 | Multi-agent orchestration |
| LLM | OCI GenAI (Cohere Command R+) | Code generation & review |
| Backend | Python FastAPI 3.11+ | REST API server |
| Frontend | Oracle APEX 24.1+ | UI / CRUD / Reports |
| Database | OCI Autonomous DB 26ai | Data + Vector Search + ONNX + Select AI |
| Code Editor | Monaco Editor | Syntax highlighting + diff view |
| Diagrams | Mermaid.js | Architecture diagram rendering |
| Secrets | OCI Vault | API keys, DB credentials |
| Gateway | OCI API Gateway | Rate limiting, CORS, auth |
| Infra | Terraform >=1.5 | Self-provisioning |

---

## Why ADB 26ai?

ADB 26ai is not just a database — it's an AI data platform baked directly into Oracle's cloud:

- **Native `VECTOR` type + HNSW index** — No external vector DB required; store and query embeddings alongside your relational data
- **In-database ONNX embedding model** — Zero external API calls for generating embeddings; the model runs inside ADB
- **Hybrid Search** — Vector similarity + full-text + standard SQL in a single query
- **Select AI** — Users can query the Gold Standard Library in plain English, no SQL required
- **JSON-Relational Duality Views** — Expose table data as REST endpoints via ORDS without writing extra code
- **Quantum-resistant encryption** — Enterprise-grade security out of the box

---

## Project Structure

```
Proviso/
├── backend/
│   ├── main.py
│   ├── agents/          # CrewAI agents (generator, reviewer, cleanup, crew)
│   ├── prompts/         # Version-controlled prompt templates
│   ├── llm/             # OCI GenAI wrapper for CrewAI
│   ├── routers/         # FastAPI route handlers
│   ├── services/        # Business logic, diff engine
│   └── db/              # ADB connection, repositories
├── apex/
│   ├── js/              # monaco-loader.js, mermaid-renderer.js
│   └── css/
├── terraform/           # IaC for Proviso's own infrastructure
├── AGENT.md             # Deep agent technical spec
├── .env.example
└── docker-compose.yml
```

---

## Prerequisites

Before you start, make sure you have:

- [ ] OCI account with credits + API signing key configured
- [ ] OCI CLI installed and configured (`oci setup config`)
- [ ] Python 3.11+
- [ ] Docker (for containerised deployment)
- [ ] **OCI GenAI quota confirmed** — test the API from your region before doing anything else; this is the most common early blocker
- [ ] ADB 26ai instance provisioned with APEX enabled

---

## Getting Started

```bash
# 1. Clone
git clone https://github.com/iRajesha/Proviso.git
cd Proviso

# 2. Python environment
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your OCI credentials, GenAI endpoint, ADB connection

# 4. Verify OCI GenAI access (critical — do this first)
python3 -c "
import oci
config = oci.config.from_file()
client = oci.generative_ai_inference.GenerativeAiInferenceClient(config)
print('OCI GenAI client ready:', client.base_client.endpoint)
"

# 5. Run the API server
uvicorn main:app --reload --port 8000

# 6. Test generation
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test",
    "requestor": "team",
    "environment": "Development",
    "requirement": "Simple VCN with one compute instance",
    "services": ["Compute"],
    "nfr": "",
    "include_cleanup": true
  }'
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
OCI_REGION=us-chicago-1
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxxx
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx
OCI_GENAI_ENDPOINT=https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130
OCI_GENAI_MODEL_ID=cohere.command-r-plus
OCI_GENAI_API_KEY=your_api_key_here
ADB_DSN=your_adb_connection_string
ADB_USER=WORKBENCH_USER
ADB_PASSWORD=stored_in_vault
API_PORT=8000
LOG_LEVEL=INFO
```

> ⚠️ Never commit your `.env` file. It is listed in `.gitignore` by default.

---

## OCI IAM Policies

Add the following policies to allow the Proviso service identity to access required OCI services:

```
Allow group InfraAgentGroup to use generative-ai-family in compartment <compartment>
Allow group InfraAgentGroup to manage autonomous-databases in compartment <compartment>
Allow group InfraAgentGroup to manage objects in compartment <compartment>
Allow group InfraAgentGroup to use vaults in compartment <compartment>
Allow group InfraAgentGroup to use keys in compartment <compartment>
Allow group InfraAgentGroup to manage api-gateway-family in compartment <compartment>
```

---

## Docker Deployment

```bash
docker build -t proviso-api ./backend
docker run -p 8000:8000 --env-file .env proviso-api
# or with docker-compose
docker-compose up -d
```

---

## Database Setup

See [AGENT.md](./AGENT.md) for the full DDL. High-level steps:

1. Run schema DDL to create tables: `projects`, `generated_scripts`, `review_history`, `gold_standards`, `keywords`
2. Load the ONNX embedding model into ADB 26ai
3. Create the HNSW vector index on the embeddings column
4. Enable the Select AI profile pointing to your OCI GenAI credentials
5. Create JSON Duality Views for ORDS REST access

---

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/generate` | Run the full 3-agent pipeline (generate → review → cleanup) |
| `POST` | `/api/v1/review` | Apply human feedback and re-run the review agent |
| `POST` | `/api/v1/scripts/save` | Save a reviewed script to the Gold Standard Library |
| `GET` | `/api/v1/scripts/search` | Hybrid search the Gold Library (vector + full-text) |

---

## Demo Flow

The happy path from browser to working Terraform in under 2 minutes:

```
1. Open Proviso in Oracle APEX
   └─▶ Navigate to "New Infrastructure Request"

2. Fill in the form
   ├─ Project: "prod-web-tier"
   ├─ Environment: Production
   ├─ Requirement: "HA web tier: 2 compute instances behind a public load balancer,
   │               private subnet, NSG rules for HTTP/HTTPS only, block storage attached"
   └─ Services: [Compute, Load Balancer, Networking, Block Storage]

3. Click "Generate"
   └─▶ POST /api/v1/generate
       ├─ Agent 1 (Generator)  → produces oci_core_vcn, oci_core_subnet,
       │                          oci_load_balancer, oci_core_instance × 2, ...
       ├─ Agent 2 (Reviewer)   → checks CIS OCI; adds encryption flags,
       │                          restricts NSG egress, enforces private endpoints
       └─ Agent 3 (Cleanup)    → writes terraform destroy sequence + null_resource hooks

4. Review the diff
   └─▶ Monaco Diff Editor shows Agent 1 output (left) vs Agent 2 corrections (right)
       └─ All CIS changes highlighted inline

5. Save to Gold Library (optional)
   └─▶ Add keywords: ["ha", "web-tier", "load-balancer", "production"]
       └─▶ POST /api/v1/scripts/save  →  stored with HNSW vector index in ADB 26ai

6. Download & apply
   └─▶ terraform init && terraform plan && terraform apply
```

---

## Sprint Plan

### Week 1 — Foundation + Core Generation (Days 1–5)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| D1 | Project scaffolding: FastAPI + CrewAI + Docker | Dev 1 | Running FastAPI with health endpoint |
| D1 | ADB 26ai setup + schema + ONNX model load | Dev 2 | Tables created, vector index + embedding trigger working |
| D1 | OCI GenAI access setup + IAM policies | Dev 2 | GenAI API callable from CLI |
| D2 | OCI GenAI LLM wrapper for CrewAI | Dev 1 | `get_oci_llm()` returns working LLM |
| D2 | Generator agent + prompt engineering | Dev 1 | Agent 1 produces real OCI Terraform |
| D2 | APEX app skeleton: Page 1 layout, navigation | Dev 2 | Basic UI structure in APEX |
| D3 | Reviewer agent + CIS compliance prompt | Dev 1 | Agent 2 reviews and corrects TF |
| D3 | Crew assembly + sequential pipeline | Dev 1 | Full crew runs: generate → review |
| D3 | Monaco Editor integration in APEX | Dev 2 | Code viewer renders HCL |
| D4 | `/api/v1/generate` endpoint (end-to-end) | Dev 1 | API returns real generated scripts |
| D4 | APEX → FastAPI integration (Ajax Callback) | Dev 2 | "Generate" button triggers real API |
| D5 | Diff service + Monaco Diff Editor | Dev 1+2 | Side-by-side diff visible in APEX |
| D5 | Integration testing + bug fixes | All | End-to-end flow working |

### Week 2 — Polish + Remaining Use Cases (Days 6–10)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| D6 | Cleanup agent (Agent 3) + pipeline integration | Dev 1 | Cleanup scripts generated |
| D6 | Mermaid diagram rendering in APEX | Dev 2 | Architecture diagram shows in UI |
| D7 | Human feedback review flow (UC2 iteration) | Dev 1 | User can ask agent to correct |
| D7 | Save as Gold Standard (form + DB write) | Dev 2 | Scripts saved with keywords |
| D8 | Search/Library page (APEX IR + API) | Dev 2 | Page 2: search, filter, download |
| D8 | Vector + hybrid search integration (ADB 26ai) | Dev 1 | Semantic + full-text + SQL search in single query |
| D9 | UI polish: loading states, error handling, UX | Dev 2 | Production-quality feel |
| D9 | Prompt tuning: test 10+ requirement scenarios | Dev 1 | Consistent quality output |
| D10 | Demo rehearsal + final bug fixes | All | Demo-ready application |
| D10 | Presentation deck finalization | All | Slide deck polished |

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | OCI GenAI output quality inconsistent | High | High | Extensive prompt engineering with few-shot examples; fallback to `temperature=0.1` |
| R2 | OCI GenAI rate limiting / quota exceeded | Medium | High | Set `max_rpm=10` in crew; cache responses; request quota increase early |
| R3 | CrewAI + OCI GenAI integration issues | Medium | High | Direct OCI SDK fallback (`OCIGenAIDirectLLM` class ready) |
| R4 | Generation takes >60s (APEX/API timeout) | Medium | Medium | Async polling: POST returns `job_id`, GET polls status |
| R5 | Generated Terraform has syntax errors | High | Medium | Agent 2 catches most issues; add `terraform validate` as post-step |
| R6 | APEX UI development slower than expected | Medium | Medium | Fallback: use Streamlit for demo; APEX for production story |
| R7 | ADB 26ai Vector Search setup complexity | Low | Low | Fallback: keyword-based LIKE search; HNSW index is a bonus |
| R8 | Team bandwidth (2 devs × 2 weeks) | Medium | High | Ruthlessly cut scope to UC1+UC2+UC3; UC4+UC5 are stretch goals |

---

## See Also

- [**AGENT.md**](./AGENT.md) — Deep technical spec for the AI agent layer, prompt engineering, OCI GenAI integration, API contracts, and full database DDL

---

## License

[MIT](./LICENSE) © Proviso Contributors
