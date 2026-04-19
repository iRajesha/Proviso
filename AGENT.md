# AGENT.md — Proviso AI Agent Technical Specification

> **Audience:** Developers building and extending the AI agent layer.  
> For project overview, setup, and deployment see [README.md](./README.md).

---

## Table of Contents

1. [Agent Pipeline Overview](#1-agent-pipeline-overview)
2. [CrewAI Agent Definitions](#2-crewai-agent-definitions)
3. [Crew Assembly](#3-crew-assembly)
4. [OCI GenAI LLM Integration](#4-oci-genai-llm-integration)
5. [Prompt Engineering](#5-prompt-engineering)
6. [Generation Service](#6-generation-service)
7. [Diff Service](#7-diff-service)
8. [Human Feedback Review Loop](#8-human-feedback-review-loop)
9. [Database Layer (ADB 26ai)](#9-database-layer-adb-26ai)
10. [API Contracts](#10-api-contracts)
11. [APEX Frontend Integration](#11-apex-frontend-integration)

---

## 1. Agent Pipeline Overview

Proviso uses a **sequential 3-agent CrewAI pipeline**. Each agent receives the output of the previous agent as context.

```
User NL Input
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  CrewAI Crew (Process.sequential)                               │
│                                                                 │
│  ┌──────────────────┐                                          │
│  │  Agent 1          │  Role: Senior OCI Infrastructure Architect│
│  │  GENERATOR        │  Input: NL requirements + services       │
│  │                   │  Output: Raw Terraform HCL               │
│  └────────┬─────────┘                                          │
│           │ (output passed as context)                         │
│           ▼                                                    │
│  ┌──────────────────┐                                          │
│  │  Agent 2          │  Role: OCI Security & Compliance Reviewer│
│  │  REVIEWER         │  Input: Agent 1 Terraform               │
│  │                   │  Output: Corrected TF + change summary   │
│  └────────┬─────────┘                                          │
│           │ (output passed as context)                         │
│           ▼                                                    │
│  ┌──────────────────┐                                          │
│  │  Agent 3          │  Role: Infrastructure Cleanup Specialist │
│  │  CLEANUP          │  Input: Agent 2 corrected Terraform      │
│  │                   │  Output: Bash destroy/rollback script    │
│  └──────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
FastAPI response → APEX UI
(original_tf, reviewed_tf, change_summary, cleanup_script, mermaid_diagram, diff)
```

**Human feedback loop** (post-pipeline): A 4th on-demand **Correction Agent** spins up when the user requests changes in the review chat. It receives the current Terraform + conversation history and applies targeted corrections.

---

## 2. CrewAI Agent Definitions

### File: `backend/agents/generator_agent.py`

```python
from crewai import Agent
from backend.llm.oci_genai_llm import get_oci_llm


def create_generator_agent() -> Agent:
    return Agent(
        role="Senior OCI Infrastructure Architect",
        goal=(
            "Generate production-grade, runnable Terraform code for Oracle Cloud "
            "Infrastructure based on the user's natural language requirements. "
            "Use real oci_ provider resources — never placeholder modules."
        ),
        backstory=open("prompts/generator_backstory.md").read(),
        llm=get_oci_llm(),
        verbose=True,
        max_iter=3,
        allow_delegation=False,
    )
```

### File: `backend/agents/reviewer_agent.py`

```python
from crewai import Agent
from backend.llm.oci_genai_llm import get_oci_llm


def create_reviewer_agent() -> Agent:
    return Agent(
        role="OCI Security & Compliance Reviewer",
        goal=(
            "Review Terraform code for OCI security best practices, "
            "CIS benchmark compliance, and architectural correctness. "
            "Output the corrected Terraform AND a structured change summary."
        ),
        backstory=open("prompts/reviewer_backstory.md").read(),
        llm=get_oci_llm(),
        verbose=True,
        max_iter=2,
        allow_delegation=False,
    )
```

### File: `backend/agents/cleanup_agent.py`

```python
from crewai import Agent
from backend.llm.oci_genai_llm import get_oci_llm


def create_cleanup_agent() -> Agent:
    return Agent(
        role="Infrastructure Cleanup Specialist",
        goal=(
            "Generate a safe bash cleanup/rollback script that destroys "
            "OCI resources in the correct dependency order. Include safety "
            "checks, confirmation prompts, and logging."
        ),
        backstory=open("prompts/cleanup_backstory.md").read(),
        llm=get_oci_llm(),
        verbose=True,
        max_iter=2,
        allow_delegation=False,
    )
```

---

## 3. Crew Assembly

### File: `backend/agents/crew.py`

```python
from crewai import Crew, Task, Process
from backend.agents.generator_agent import create_generator_agent
from backend.agents.reviewer_agent import create_reviewer_agent
from backend.agents.cleanup_agent import create_cleanup_agent


def build_generation_crew():
    """Assemble the full 3-agent generation crew."""

    generator = create_generator_agent()
    reviewer = create_reviewer_agent()
    cleanup = create_cleanup_agent()

    # Task 1: Generate Terraform
    generate_task = Task(
        description=(
            "Generate complete, runnable OCI Terraform code for:\n"
            "Project: {project_name}\n"
            "Environment: {environment}\n"
            "Requirements: {requirement}\n"
            "OCI Services: {services}\n"
            "Non-functional requirements: {nfr}\n\n"
            "Rules:\n"
            "- Use terraform oci provider with real resource types\n"
            "- Include variables.tf, outputs.tf content\n"
            "- Add proper tagging with project_name and environment\n"
            "- Create VCN, subnets, security lists, route tables\n"
            "- Follow least-privilege IAM\n"
            "- Output ONLY valid Terraform HCL code"
        ),
        agent=generator,
        expected_output=(
            "Complete Terraform code with: provider block, VCN/subnet setup, "
            "all requested OCI service resources, variables, outputs, and tags."
        ),
    )

    # Task 2: Review for security & compliance
    review_task = Task(
        description=(
            "Review the Terraform code from the generator agent.\n"
            "Check against these CIS OCI Benchmark rules:\n"
            "1. No public IPs on databases or app servers\n"
            "2. NSGs on all compute/db resources\n"
            "3. Encryption at rest enabled (ADB, Object Storage, Block Volume)\n"
            "4. WAF or rate limiting on public endpoints\n"
            "5. IAM policies follow least privilege\n"
            "6. Logging and monitoring enabled\n"
            "7. Backup policies defined\n"
            "8. No hardcoded credentials\n\n"
            "Output TWO sections:\n"
            "SECTION 1 - CORRECTED TERRAFORM: The full corrected code\n"
            "SECTION 2 - CHANGE SUMMARY: Bullet list of every change made and why"
        ),
        agent=reviewer,
        expected_output=(
            "SECTION 1: Full corrected Terraform code. "
            "SECTION 2: Bullet list of changes made with justifications."
        ),
        context=[generate_task],
    )

    # Task 3: Generate cleanup script
    cleanup_task = Task(
        description=(
            "Based on the reviewed Terraform code, generate a bash cleanup script.\n"
            "The script must:\n"
            "- Destroy resources in reverse dependency order\n"
            "- Use terraform destroy as primary method\n"
            "- Include OCI CLI fallback commands for manual cleanup\n"
            "- Add confirmation prompt before destructive actions\n"
            "- Log all actions to a cleanup log file\n"
            "- Handle errors gracefully (don't stop on first failure)\n"
            "- Output ONLY a valid bash script"
        ),
        agent=cleanup,
        expected_output="Complete bash cleanup script with safety checks and logging.",
        context=[review_task],
    )

    crew = Crew(
        agents=[generator, reviewer, cleanup],
        tasks=[generate_task, review_task, cleanup_task],
        process=Process.sequential,
        verbose=True,
        memory=False,   # Keep simple for hackathon
        max_rpm=10,     # Rate limit to avoid OCI GenAI throttling
    )

    return crew, generate_task, review_task, cleanup_task
```

---

## 4. OCI GenAI LLM Integration

### File: `backend/llm/oci_genai_llm.py`

```python
import os
from crewai import LLM


def get_oci_llm() -> LLM:
    """
    Create OCI GenAI LLM instance for CrewAI.
    CrewAI uses litellm under the hood.
    OCI GenAI exposes an OpenAI-compatible endpoint.
    """
    return LLM(
        model="openai/cohere.command-r-plus",  # litellm provider prefix
        base_url=os.getenv(
            "OCI_GENAI_ENDPOINT",
            "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130"
        ),
        api_key=os.getenv("OCI_GENAI_API_KEY"),
        temperature=0.2,       # Low temp for deterministic code generation
        max_tokens=4096,
        custom_llm_provider="openai",
    )


def get_embedding_fn():
    """
    Returns a function that generates embeddings via in-database ONNX model.
    With ADB 26ai, embeddings run IN-DATABASE — no external API call needed.
    Used only for query-side embedding during semantic search.
    """
    import oracledb

    conn = oracledb.connect(
        dsn=os.getenv("ADB_DSN_PROVISO"),
        user=os.getenv("ADB_USER_PROVISO"),
        password=os.getenv("ADB_PASSWORD_PROVISO")
    )
    cursor = conn.cursor()

    def embed_text(text: str) -> list[float]:
        cursor.execute("""
            SELECT TO_VECTOR(DBMS_VECTOR.UTL_TO_EMBEDDING(
                :text_input,
                JSON('{"provider":"database","model":"ALL_MINILM_L12_V2"}')
            )) FROM DUAL
        """, {"text_input": text})
        return cursor.fetchone()[0]

    return embed_text
```

### Fallback: Direct OCI SDK (if litellm/OpenAI-compat endpoint doesn't work)

```python
import os
import oci


class OCIGenAIDirectLLM:
    """
    Direct OCI SDK fallback — use if the OpenAI-compatible endpoint
    has issues with litellm. Swap into get_oci_llm() as needed.
    """

    def __init__(self):
        self.config = oci.config.from_file()
        self.client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            self.config
        )
        self.model_id = os.getenv("OCI_GENAI_MODEL_ID", "cohere.command-r-plus")
        self.compartment_id = os.getenv("OCI_COMPARTMENT_ID")

    def call(self, messages: list[dict], **kwargs) -> str:
        prompt = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        response = self.client.generate_text(
            oci.generative_ai_inference.models.GenerateTextDetails(
                compartment_id=self.compartment_id,
                serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                    model_id=self.model_id
                ),
                inference_request=oci.generative_ai_inference.models.CohereLlmInferenceRequest(
                    prompt=prompt,
                    max_tokens=4096,
                    temperature=0.2,
                )
            )
        )
        return response.data.inference_response.generated_texts[0].text
```

---

## 5. Prompt Engineering

All prompts are stored as `.md` files under `backend/prompts/` and version-controlled separately from code. This allows iterating on prompts without touching Python.

### File: `backend/prompts/generator_backstory.md`

```
You are a Senior Oracle Cloud Infrastructure (OCI) Architect with 10+ years
of experience writing production Terraform for Fortune 500 companies.

You ALWAYS use real OCI Terraform provider resources (oci_*). You NEVER
generate placeholder modules or pseudo-code.

Your Terraform code MUST include:
1. terraform {} block with required_providers (oci >= 5.0)
2. provider "oci" {} with region variable
3. Real resource blocks: oci_core_vcn, oci_core_subnet, oci_core_security_list,
   oci_core_internet_gateway, oci_core_nat_gateway, oci_core_route_table,
   oci_identity_compartment, etc.
4. variables.tf content with: region, compartment_ocid, tenancy_ocid, project tags
5. outputs.tf with key resource OCIDs
6. Consistent tagging:
   freeform_tags = { "Project" = var.project_name, "Environment" = var.environment }
7. Proper dependency ordering using depends_on where implicit deps aren't clear

Common OCI resource patterns you know:
- VCN + public/private subnets + IGW + NAT GW + service gateway
- Autonomous Database (oci_database_autonomous_database) with private endpoint
- Load Balancer (oci_load_balancer_load_balancer) with backend sets
- Compute (oci_core_instance) with cloud-init
- OKE (oci_containerengine_cluster + oci_containerengine_node_pool)
- Object Storage (oci_objectstorage_bucket)
- Vault (oci_kms_vault + oci_kms_key)
- Functions (oci_functions_application + oci_functions_function)
- API Gateway (oci_apigateway_gateway + oci_apigateway_deployment)

Output ONLY valid HCL code. No explanations before or after the code block.
```

### File: `backend/prompts/reviewer_backstory.md`

```
You are an OCI Security & Compliance Specialist certified in CIS OCI
Foundations Benchmark v2.0. You review Terraform code for security gaps.

For EVERY review, check these mandatory rules:

NETWORKING:
- Default security list must not allow unrestricted ingress (0.0.0.0/0)
- Use NSGs (oci_core_network_security_group) instead of security lists where possible
- VCN flow logs must be enabled
- Database subnets must NOT have public IPs
- Use service gateway for Oracle services traffic (not NAT)

COMPUTE:
- No SSH access from 0.0.0.0/0 — restrict to bastion or specific CIDR
- Enable in-transit encryption

DATABASE:
- ADB must use private endpoint (subnet_id required, no public endpoint)
- ADB must have customer-managed encryption key (kms_key_id)
- Automatic backups must be enabled (backup_retention_period_in_days >= 7)

STORAGE:
- Object Storage buckets must have default encryption enabled
- No public buckets unless explicitly required in the user's requirement

IAM:
- No "manage all-resources in tenancy" policies — use least privilege
- Use dynamic groups for instance principals where possible

LOGGING:
- Enable OCI audit log retention (>= 365 days)
- Enable VCN flow logs

Your output format MUST be exactly:

SECTION 1 - CORRECTED TERRAFORM:
```hcl
(full corrected Terraform code here — no truncation)
```

SECTION 2 - CHANGE SUMMARY:
• [CATEGORY] Description of change made (CIS rule reference)
• [CATEGORY] Description of change made (CIS rule reference)
```

### File: `backend/prompts/cleanup_backstory.md`

```
You are an Infrastructure Cleanup Specialist who writes safe, idempotent
bash scripts to destroy OCI infrastructure provisioned by Terraform.

Your cleanup scripts MUST:
1. Start with #!/usr/bin/env bash and set -euo pipefail
2. Prompt the user for confirmation before any destructive action
3. Use terraform destroy as the primary destruction method
4. Include OCI CLI fallback commands for resources that Terraform may miss
5. Destroy resources in correct dependency order:
   - Application layer first (Functions, OKE workloads, Compute)
   - Load Balancers and API Gateways
   - Database layer (ADB)
   - Storage (Object Storage buckets — empty before delete)
   - Networking last (subnets, NSGs, security lists, VCN)
6. Log every action with timestamp to a cleanup.log file
7. Handle errors gracefully — log failures and continue (don't exit on first error)
8. End with a summary of what was destroyed and what may need manual cleanup

Output ONLY a valid bash script. No explanations before or after.
```

---

## 6. Generation Service

### File: `backend/services/generation_service.py`

```python
import uuid
import re
from backend.agents.crew import build_generation_crew
from backend.services.diff_service import generate_diff_html
from backend.routers.generate import GenerateRequest, GenerateResponse


def parse_review_output(raw_output: str) -> tuple[str, str]:
    """Split reviewer output into corrected terraform and change summary."""
    terraform = ""
    summary = ""

    if "SECTION 1" in raw_output and "SECTION 2" in raw_output:
        parts = raw_output.split("SECTION 2")
        terraform_part = parts[0].replace("SECTION 1", "").strip()
        summary = parts[1].strip() if len(parts) > 1 else ""

        code_match = re.search(
            r'```(?:hcl|terraform)?\n(.*?)```', terraform_part, re.DOTALL
        )
        terraform = code_match.group(1) if code_match else terraform_part
    else:
        code_match = re.search(
            r'```(?:hcl|terraform)?\n(.*?)```', raw_output, re.DOTALL
        )
        terraform = code_match.group(1) if code_match else raw_output
        summary = "Review completed — see diff for details."

    return terraform.strip(), summary.strip()


def generate_mermaid_diagram(services: list[str]) -> str:
    """Generate a Mermaid architecture diagram from the selected OCI services."""
    lines = ["graph TB"]
    lines.append('    Internet["🌐 Internet"]')
    lines.append('    VCN["OCI VCN"]')
    lines.append('    PubSub["Public Subnet"]')
    lines.append('    PrivSub["Private Subnet"]')
    lines.append('    Internet --> VCN')
    lines.append('    VCN --> PubSub')
    lines.append('    VCN --> PrivSub')

    normalized = [s.lower() for s in services]
    has = lambda name: any(name in s for s in normalized)  # noqa: E731

    if has("load balancer"):
        lines.append('    PubSub --> LB["⚖️ Load Balancer"]')
    if has("api gateway"):
        lines.append('    PubSub --> APIGW["🔌 API Gateway"]')
    if has("compute"):
        lines.append('    PrivSub --> Compute["🖥️ Compute VM"]')
        if has("load balancer"):
            lines.append('    LB --> Compute')
    if has("oke"):
        lines.append('    PrivSub --> OKE["☸️ OKE Cluster"]')
        if has("load balancer"):
            lines.append('    LB --> OKE')
    if has("apex"):
        lines.append('    PrivSub --> APEX["🧩 Oracle APEX"]')
    if has("autonomous"):
        lines.append('    PrivSub --> ADB["🗄️ Autonomous DB"]')
        if has("apex"):
            lines.append('    APEX --> ADB')
    if has("object storage"):
        lines.append('    PrivSub --> ObjStore["📦 Object Storage"]')
    if has("vault"):
        lines.append('    PrivSub --> Vault["🔐 OCI Vault"]')
    if has("functions"):
        lines.append('    PrivSub --> Functions["⚡ OCI Functions"]')
        if has("api gateway"):
            lines.append('    APIGW --> Functions')

    return "\n".join(lines)


async def run_generation(req: GenerateRequest) -> GenerateResponse:
    """Execute the full CrewAI 3-agent generation pipeline."""
    job_id = str(uuid.uuid4())[:8]

    crew, gen_task, rev_task, cleanup_task = build_generation_crew()

    inputs = {
        "project_name": req.project_name,
        "environment": req.environment,
        "requirement": req.requirement,
        "services": ", ".join(req.services),
        "nfr": req.nfr or "Standard OCI security best practices",
    }

    # Synchronous for hackathon — for production use background task + polling
    crew.kickoff(inputs=inputs)

    original_tf = gen_task.output.raw if gen_task.output else ""
    review_raw = rev_task.output.raw if rev_task.output else ""
    cleanup_raw = cleanup_task.output.raw if cleanup_task.output else ""

    reviewed_tf, change_summary = parse_review_output(review_raw)
    diff_html = generate_diff_html(original_tf, reviewed_tf)
    mermaid = generate_mermaid_diagram(req.services)

    cleanup_match = re.search(
        r'```(?:bash|sh)?\n(.*?)```', cleanup_raw, re.DOTALL
    )
    cleanup_script = cleanup_match.group(1) if cleanup_match else cleanup_raw

    return GenerateResponse(
        job_id=job_id,
        status="completed",
        original_terraform=original_tf,
        reviewed_terraform=reviewed_tf,
        change_summary=change_summary,
        cleanup_script=cleanup_script if req.include_cleanup else None,
        mermaid_diagram=mermaid,
        diff_html=diff_html,
    )
```

---

## 7. Diff Service

### File: `backend/services/diff_service.py`

```python
import difflib


def generate_diff_html(original: str, reviewed: str) -> str:
    """Generate a unified diff string between original and reviewed Terraform."""
    original_lines = original.splitlines(keepends=True)
    reviewed_lines = reviewed.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        reviewed_lines,
        fromfile="Original (Agent 1)",
        tofile="Reviewed (Agent 2)",
        lineterm=""
    )
    return "\n".join(diff)


def generate_side_by_side(original: str, reviewed: str) -> dict:
    """
    Returns side-by-side diff payload for Monaco Diff Editor.
    Pass this dict's values directly to diffEditor.setModel().
    """
    return {
        "original": original,
        "modified": reviewed,
        "language": "hcl",
    }
```

---

## 8. Human Feedback Review Loop

After the 3-agent pipeline completes, the user can request corrections in natural language via the APEX review chat. A 4th on-demand **Correction Agent** handles each round.

### File: `backend/services/review_service.py`

```python
from crewai import Agent, Task, Crew, Process
from backend.llm.oci_genai_llm import get_oci_llm
from backend.services.diff_service import generate_diff_html


async def apply_human_feedback(
    current_terraform: str,
    feedback: str,
    conversation_history: list[dict],
) -> dict:
    """
    Apply user's natural language feedback to the current Terraform.
    Spawns a single-agent crew for each feedback round.

    Args:
        current_terraform: The Terraform code currently shown to the user
        feedback: User's natural language correction request
        conversation_history: List of {"role": "user|agent", "message": "..."} dicts
    """
    correction_agent = Agent(
        role="OCI Terraform Correction Specialist",
        goal=(
            "Apply the user's requested corrections to the Terraform code. "
            "Preserve all existing resources. Only change what was requested."
        ),
        backstory=(
            "You are an expert at modifying OCI Terraform code based on user "
            "feedback. You make surgical changes — you never rewrite working code "
            "unless explicitly asked to."
        ),
        llm=get_oci_llm(),
        verbose=True,
    )

    history_text = "\n".join(
        f"{h['role'].upper()}: {h['message']}"
        for h in conversation_history
    )

    correction_task = Task(
        description=(
            f"Current Terraform code:\n```hcl\n{current_terraform}\n```\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"User's latest feedback: {feedback}\n\n"
            "Apply the corrections. Output:\n"
            "SECTION 1 - CORRECTED TERRAFORM: the full updated code\n"
            "SECTION 2 - CHANGES MADE: bullet list of exactly what you changed"
        ),
        agent=correction_agent,
        expected_output="SECTION 1: corrected code. SECTION 2: change bullets.",
    )

    crew = Crew(
        agents=[correction_agent],
        tasks=[correction_task],
        process=Process.sequential,
        verbose=True,
    )
    crew.kickoff()

    corrected_tf = correction_task.output.raw
    diff_html = generate_diff_html(current_terraform, corrected_tf)

    return {
        "corrected_terraform": corrected_tf,
        "diff_html": diff_html,
    }
```

### File: `backend/routers/review.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.services.review_service import apply_human_feedback

router = APIRouter()


class ReviewRequest(BaseModel):
    script_id: str
    current_terraform: str
    feedback: str
    conversation_history: list[dict] = []


class ReviewResponse(BaseModel):
    corrected_terraform: str
    change_summary: Optional[str] = None
    diff_html: str


@router.post("/review", response_model=ReviewResponse)
async def review_with_feedback(req: ReviewRequest):
    result = await apply_human_feedback(
        current_terraform=req.current_terraform,
        feedback=req.feedback,
        conversation_history=req.conversation_history,
    )
    return ReviewResponse(
        corrected_terraform=result["corrected_terraform"],
        diff_html=result["diff_html"],
    )
```

---

## 9. Database Layer (ADB 26ai)

### Schema DDL

```sql
-------------------------------------------------
-- SETUP: Enable AI features in ADB 26ai
-------------------------------------------------
BEGIN
    DBMS_CLOUD_AI.CREATE_PROFILE(
        profile_name => 'OCI_GENAI_PROFILE',
        attributes   => '{"provider": "oci",
                          "model": "cohere.command-r-plus",
                          "credential_name": "OCI_GENAI_CRED",
                          "oci_compartment_id": "<compartment_ocid>"}'
    );
END;
/

-- Register ONNX embedding model (eliminates external embedding API calls)
BEGIN
    DBMS_VECTOR.LOAD_ONNX_MODEL(
        model_name => 'ALL_MINILM_L12_V2',
        model_data => <onnx_model_blob>,
        metadata   => JSON('{"function":"embedding","input":"text"}')
    );
END;
/

-------------------------------------------------
-- CORE TABLES
-------------------------------------------------
CREATE TABLE projects (
    project_id      VARCHAR2(36)  DEFAULT sys_guid() PRIMARY KEY,
    project_name    VARCHAR2(200) NOT NULL,
    requestor       VARCHAR2(200),
    environment     VARCHAR2(50)  DEFAULT 'Development',
    requirement     CLOB,
    nfr             CLOB,
    services        CLOB,           -- JSON array: ["Compute","ADB"]
    created_at      TIMESTAMP     DEFAULT SYSTIMESTAMP,
    created_by      VARCHAR2(100)
);

CREATE TABLE generated_scripts (
    script_id           VARCHAR2(36)  DEFAULT sys_guid() PRIMARY KEY,
    project_id          VARCHAR2(36)  REFERENCES projects(project_id),
    original_terraform  CLOB,         -- Agent 1 output (raw)
    reviewed_terraform  CLOB,         -- Agent 2 corrected output
    change_summary      CLOB,         -- What Agent 2 changed
    cleanup_script      CLOB,         -- Agent 3 output
    mermaid_diagram     CLOB,
    status              VARCHAR2(50)  DEFAULT 'generated',
    created_at          TIMESTAMP     DEFAULT SYSTIMESTAMP
);

CREATE TABLE review_history (
    review_id       VARCHAR2(36)  DEFAULT sys_guid() PRIMARY KEY,
    script_id       VARCHAR2(36)  REFERENCES generated_scripts(script_id),
    feedback        CLOB,
    corrected_tf    CLOB,
    diff_html       CLOB,
    turn_number     NUMBER(3)     DEFAULT 1,
    created_at      TIMESTAMP     DEFAULT SYSTIMESTAMP
);

CREATE TABLE gold_standards (
    gold_id         VARCHAR2(36)  DEFAULT sys_guid() PRIMARY KEY,
    script_id       VARCHAR2(36)  REFERENCES generated_scripts(script_id),
    label           VARCHAR2(300) NOT NULL,
    description     CLOB,
    is_gold         NUMBER(1)     DEFAULT 1,
    final_terraform CLOB          NOT NULL,
    cleanup_script  CLOB,
    mermaid_diagram CLOB,
    created_at      TIMESTAMP     DEFAULT SYSTIMESTAMP,
    created_by      VARCHAR2(100),
    -- ADB 26ai: native VECTOR type for semantic search
    description_vec VECTOR(1024, FLOAT64)
);

CREATE TABLE keywords (
    keyword_id  VARCHAR2(36)  DEFAULT sys_guid() PRIMARY KEY,
    gold_id     VARCHAR2(36)  REFERENCES gold_standards(gold_id),
    keyword     VARCHAR2(100) NOT NULL
);

CREATE INDEX idx_keywords_keyword ON keywords(UPPER(keyword));

-------------------------------------------------
-- ADB 26ai: HNSW Vector Index
-------------------------------------------------
CREATE VECTOR INDEX idx_gold_vec ON gold_standards(description_vec)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95
    PARAMETERS (type HNSW, neighbors 16, efconstruction 200);

-------------------------------------------------
-- ADB 26ai: Auto-embed on insert/update (no external API call)
-------------------------------------------------
CREATE OR REPLACE TRIGGER trg_gold_embedding
BEFORE INSERT OR UPDATE OF description ON gold_standards
FOR EACH ROW
BEGIN
    :NEW.description_vec := DBMS_VECTOR.UTL_TO_EMBEDDING(
        :NEW.description,
        JSON('{"provider":"database","model":"ALL_MINILM_L12_V2"}')
    );
END;
/

-------------------------------------------------
-- ADB 26ai: Hybrid Search (vector + full-text + SQL in one query)
-------------------------------------------------
-- Usage: pass :query_vec (from embed_text()) and :text_query
SELECT gold_id, label, description, is_gold,
       VECTOR_DISTANCE(description_vec, :query_vec, COSINE) AS similarity
FROM gold_standards
WHERE is_gold = 1
  AND CONTAINS(description, :text_query) > 0
  AND VECTOR_DISTANCE(description_vec, :query_vec, COSINE) < 0.5
ORDER BY similarity ASC
FETCH FIRST 10 ROWS ONLY;

-------------------------------------------------
-- ADB 26ai: Select AI — natural language queries
-------------------------------------------------
-- Set profile once per session:
-- EXEC DBMS_CLOUD_AI.SET_PROFILE('OCI_GENAI_PROFILE');
--
-- Then query in plain English:
-- SELECT AI "Show me all gold standard scripts for APEX with ADB"
-- FROM gold_standards;

-------------------------------------------------
-- ADB 26ai: JSON-Relational Duality View (REST via ORDS)
-------------------------------------------------
CREATE JSON RELATIONAL DUALITY VIEW gold_scripts_jdv AS
    gold_standards @insert @update @delete {
        _id         : gold_id
        label       : label
        description : description
        isGold      : is_gold
        terraform   : final_terraform
        cleanup     : cleanup_script
        diagram     : mermaid_diagram
        createdAt   : created_at
        createdBy   : created_by
        keywords    : keywords @insert @update @delete {
            keywordId : keyword_id
            keyword   : keyword
        }
    };
-- REST access via ORDS:
-- GET  /ords/workbench/gold_scripts_jdv/{id}
-- POST /ords/workbench/gold_scripts_jdv/
```

---

## 10. API Contracts

### `POST /api/v1/generate`

**Request:**
```json
{
  "project_name": "Customer 360 Platform",
  "requestor": "APEX Platform Team",
  "environment": "Production",
  "requirement": "Deploy APEX with ADB in private subnet, public LB, OCI Vault for secrets",
  "services": ["APEX", "Autonomous DB", "Load Balancer", "OCI Vault"],
  "nfr": "Multi-AD HA, least privilege IAM, WAF integration",
  "include_cleanup": true
}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4",
  "status": "completed",
  "original_terraform": "# Agent 1 raw output...",
  "reviewed_terraform": "# Agent 2 corrected output...",
  "change_summary": "• Added NSG...\n• Enabled encryption...",
  "cleanup_script": "#!/bin/bash\n# Cleanup...",
  "mermaid_diagram": "graph TB\n    Internet --> VCN...",
  "diff_html": "--- Original (Agent 1)\n+++ Reviewed (Agent 2)\n@@..."
}
```

### `POST /api/v1/review`

**Request:**
```json
{
  "script_id": "abc-123",
  "current_terraform": "# current reviewed code...",
  "feedback": "Add a WAF policy in front of the load balancer",
  "conversation_history": [
    {"role": "agent", "message": "Generated initial script with public LB"},
    {"role": "user", "message": "Add WAF policy"}
  ]
}
```

**Response:**
```json
{
  "corrected_terraform": "# updated code with WAF...",
  "change_summary": "• Added oci_waf_web_app_firewall resource attached to LB",
  "diff_html": "--- ...\n+++ ..."
}
```

### `POST /api/v1/scripts/save`

**Request:**
```json
{
  "script_id": "abc-123",
  "label": "APEX + ADB + LB Gold Template",
  "description": "Production-grade APEX with ADB in private subnet, public LB, OCI Vault",
  "keywords": ["apex", "adb", "production", "load-balancer", "vault"],
  "is_gold": true,
  "final_terraform": "# final reviewed and user-approved code...",
  "cleanup_script": "#!/bin/bash\n# cleanup..."
}
```

**Response:**
```json
{
  "gold_id": "xyz-789",
  "status": "saved",
  "embedding_generated": true
}
```

### `GET /api/v1/scripts/search`

**Query params:** `?q=apex+private+subnet&is_gold=true&limit=10`

**Response:**
```json
{
  "results": [
    {
      "gold_id": "xyz-789",
      "label": "APEX + ADB Gold Template",
      "description": "Production-grade APEX with ADB in private subnet...",
      "keywords": ["apex", "adb", "production"],
      "is_gold": true,
      "similarity_score": 0.92,
      "created_at": "2026-04-20T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 11. APEX Frontend Integration

### APEX Page Structure

| Page | Type | Purpose |
|------|------|---------|
| Page 1 | Form + Static HTML Regions | Requirement input → Generate → Review → Save |
| Page 2 | Interactive Report | Search & browse Gold Standard library |

**Page 1 Regions (top to bottom):**

| Region | Type | Purpose |
|--------|------|---------|
| R1: Project Info | Form | Project Name, Requestor, Environment |
| R2: Requirements | Form | NL description textarea, NFR textarea |
| R3: Service Selector | Shuttle / Checkbox | Multi-select OCI services LOV |
| R4: Options | Checkbox | Terraform ✓, Cleanup ✓ |
| R5: Generate | Button | Triggers Ajax Callback → FastAPI |
| R6: Architecture | Static HTML | Mermaid.js diagram |
| R7: Diff View | Static HTML | Monaco Diff Editor (Agent 1 vs Agent 2) |
| R8: Reviewed TF | Static HTML | Monaco Editor — corrected Terraform |
| R9: Cleanup | Static HTML | Monaco Editor — bash script |
| R10: Feedback | Form + Button | Chat-style review corrections |
| R11: Save | Form | Label, description, keywords, gold flag |

### APEX Ajax Callback: `GENERATE_INFRA` (PL/SQL)

```sql
DECLARE
    l_url       VARCHAR2(500) := 'https://your-api-gateway/api/v1/generate';
    l_body      CLOB;
    l_response  CLOB;
BEGIN
    apex_json.initialize_clob_output;
    apex_json.open_object;
    apex_json.write('project_name',  apex_application.g_x01);
    apex_json.write('requestor',     apex_application.g_x02);
    apex_json.write('environment',   apex_application.g_x03);
    apex_json.write('requirement',   apex_application.g_x04);

    apex_json.open_array('services');
    FOR i IN 1 .. apex_string.split(apex_application.g_x05, ':').COUNT LOOP
        apex_json.write(apex_string.split(apex_application.g_x05, ':')(i));
    END LOOP;
    apex_json.close_array;

    apex_json.write('nfr', apex_application.g_x06);
    apex_json.write('include_cleanup',
        CASE WHEN apex_application.g_x07 = 'Y' THEN TRUE ELSE FALSE END);
    apex_json.close_object;

    l_body := apex_json.get_clob_output;
    apex_json.free_output;

    apex_web_service.g_request_headers.DELETE;
    apex_web_service.g_request_headers(1).name  := 'Content-Type';
    apex_web_service.g_request_headers(1).value := 'application/json';

    l_response := apex_web_service.make_rest_request(
        p_url         => l_url,
        p_http_method => 'POST',
        p_body        => l_body
    );

    htp.p(l_response);
END;
```

### APEX Dynamic Action — JavaScript (on Generate button click)

```javascript
apex.server.process("GENERATE_INFRA", {
  x01: $v("P1_PROJECT_NAME"),
  x02: $v("P1_REQUESTOR"),
  x03: $v("P1_ENVIRONMENT"),
  x04: $v("P1_REQUIREMENT"),
  x05: $v("P1_SERVICES"),       // colon-separated from shuttle
  x06: $v("P1_NFR"),
  x07: $v("P1_INCLUDE_CLEANUP")
}, {
  dataType: "json",
  success: function(data) {
    apex.util.showSpinner($("body"), false);
    renderMermaid(data.mermaid_diagram);
    renderDiffEditor(data.original_terraform, data.reviewed_terraform);
    setMonacoContent("reviewed-editor", data.reviewed_terraform, "hcl");
    setMonacoContent("cleanup-editor",  data.cleanup_script,     "shell");
    document.getElementById("change-summary").innerHTML =
      data.change_summary.replace(/\n/g, "<br>");
  },
  error: function(xhr) {
    apex.message.showErrors([{
      type: "error", location: "page",
      message: "Generation failed: " + xhr.responseText
    }]);
  }
});
```

### File: `apex/js/monaco-loader.js`

```javascript
require.config({
  paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs" }
});

function renderDiffEditor(originalCode, modifiedCode) {
  require(["vs/editor/editor.main"], function () {
    const diffEditor = monaco.editor.createDiffEditor(
      document.getElementById("diff-container"),
      { theme: "vs-dark", readOnly: true, renderSideBySide: true, automaticLayout: true }
    );
    diffEditor.setModel({
      original: monaco.editor.createModel(originalCode, "hcl"),
      modified: monaco.editor.createModel(modifiedCode, "hcl"),
    });
  });
}

function setMonacoContent(containerId, code, language = "hcl") {
  require(["vs/editor/editor.main"], function () {
    monaco.editor.create(document.getElementById(containerId), {
      value: code,
      language: language,
      theme: "vs-dark",
      readOnly: true,
      minimap: { enabled: false },
      automaticLayout: true,
    });
  });
}
```

### File: `apex/js/mermaid-renderer.js`

```javascript
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";

mermaid.initialize({ startOnLoad: false, theme: "default" });

async function renderMermaid(mermaidCode) {
  const container = document.getElementById("architecture-diagram");
  const { svg } = await mermaid.render("archDiagram", mermaidCode);
  container.innerHTML = svg;
}
```

---

*For project setup, deployment, and sprint plan see [README.md](./README.md). Ship fast, iterate faster. 🚀*
