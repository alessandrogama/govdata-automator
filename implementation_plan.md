# GovData Automator - Implementation Plan (Security-Focused & Step-by-Step)

This document contains the design and implementation strategy for the **GovData Automator** project, acting under software development and information security best practices.

---

## Security Best Practices & Data Protection

As an information security and software development specialist, the following measures are enforced:
1. **Secret Management**:
   - Zero hardcoded credentials or API keys.
   - All sensitive information (webhook URLs, credentials, specific ports) will reside in `.env` files.
   - `.env` template (`.env.example`) will be committed to version control, but the actual `.env` containing sensitive data is excluded.
2. **Git Safeguards (`.gitignore`)**:
   - Prevention of accidental commits of input data (which might contain real customer CNPJs), generated output reports, runtime logs containing personal data (LGPD/GDPR compliance), python caches, and local configurations.
3. **Container Security**:
   - n8n will run under a non-root user (`node`) after packages are installed in the Dockerfile.
   - Restrict permissions to the host filesystems; write access is limited to targeted folder volumes (`/data/data/output`, `/data/logs`).
4. **Data Privacy (LGPD Compliance)**:
   - Sanitizing input data and ensuring errors/logs in `errors.jsonl` contain only structure metrics and error messages, avoiding storing sensitive internal payloads.

---

## Directory Structure

```
govdata-automator/
├── .gitignore           ← Prevents committing secrets, local logs, python caches, outputs
├── Dockerfile           ← Extends n8n to install Python, Pandas, and Requests safely
├── docker-compose.yml   ← Container orchestration with volume mounts and environment load
├── n8n/
│   ├── workflows/
│   │   ├── main_flow.json
│   │   ├── cnpj_flow.json
│   │   └── cep_flow.json
│   └── .env.example     ← n8n specific settings template
├── python/
│   ├── validate_cnpj.py
│   └── process_report.py
├── data/
│   ├── input/
│   │   └── cnpjs_exemplo.txt
│   └── output/          ← Output folder (ignored by git except for directory structure)
├── logs/
│   └── errors.jsonl     ← Append-only JSON line errors log (ignored by git)
└── README.md            ← Complete project guide (Português)
```

---

## Step-by-Step Execution Plan

I will proceed strictly step-by-step. **I will wait for your explicit approval before performing any modifications or code writes for each step.**

### Step 1: Base Configuration & Security Boundaries
- Create `.gitignore` to lock down python caches, credentials, logs, and outputs.
- Create `data/input/cnpjs_exemplo.txt` with test scenarios (valid CNPJs, invalid CNPJs, non-existing CNPJs).
- Set up directories (`data/output/`, `logs/`).

### Step 2: Python Engine Development (Offline Logic)
- Create `python/validate_cnpj.py` implementing clean mathematical check digit validation (no external libs, full type hints).
- Create `python/process_report.py` implementing Pandas post-processing, whitespace stripping, case normalization, date formatting, and duplicate removal.

### Step 3: Docker & Environment Setup
- Create `Dockerfile` for customized n8n containing Python and dependencies.
- Create `docker-compose.yml` linking the service, environment variables, and volumes.
- Create `n8n/.env.example` defining default parameters (e.g. `WEBHOOK_URL`, `N8N_PORT`).

### Step 4: n8n Workflow Construction
- Build `cnpj_flow.json` (sub-workflow): calls validate CLI, fetches BrasilAPI, handles retry and fallback/errors.
- Build `cep_flow.json` (sub-workflow): enriches records, fetches coordinates, handles retry and fallback/errors.
- Build `main_flow.json` (orchestrator): ties all stages together, writes raw outputs, executes Pandas clean-up CLI, creates JSON metrics, logs structured errors, and sends notifications.

### Step 5: Verification & Quality Assurance
- Run offline verification of validation logic.
- Run local lint checks.
- Outline steps for you to launch the environment and import workflows.

### Step 6: Finalization & Commit Message
- Write the comprehensive `README.md` (in Portuguese) with diagrams and run guidelines.
- Output the clean git commit message template.

---

## Verification Plan

### Automated Tests
- Run `python/validate_cnpj.py` CLI checks.
- Test `process_report.py` output format using Pandas manually.

### Manual Verification
- Instructions on starting Docker, loading n8n dashboard, executing the main flow, and checking generated outputs.
