# Bitlance — System Overview & Functionality Guide

## What Is Bitlance?

Bitlance is an **AI-powered freelancing intermediary platform** that removes trust friction between employers and freelancers. Instead of relying on manual reviews, reputation guesswork, or escrow services that require human arbitration — Bitlance automates the entire project lifecycle using AI.

**The core promise:**
> An employer describes a project. AI breaks it into milestones. Money is locked. A freelancer delivers work. AI verifies it. Payment releases automatically. No disputes. No delays.

---

## The Problem It Solves

Traditional freelancing platforms have three fundamental problems:

| Problem | Traditional Platform | Bitlance |
|---|---|---|
| Scope creep / vague deliverables | Employer writes milestones manually | AI auto-generates structured milestones |
| Payment disputes | Human moderator reviews | AI evaluates code/content objectively |
| Reputation gaming | Star ratings can be faked | PFI score is algorithmically calculated |

---

## How It Works — End to End

### Step 1: Employer Posts a Project

The employer opens the **Create Project** page and types a plain English description:

```
"Build a SaaS landing page with Stripe integration, user authentication,
and an admin dashboard showing analytics."
```

They also enter a **total budget** (e.g. $5,000).

**What happens behind the scenes:**
- The description is sent to the **Requirement Analysis Engine**
- GPT-4o or Claude reads the description and decomposes it into 3–8 structured milestones
- Each milestone gets: a title, description, deadline (in days), and acceptance criteria
- The milestones are saved to the database automatically
- The project is created in `draft` status

**Example AI output:**
```json
{
  "project_type": "web_application",
  "milestones": [
    { "title": "Repository & Infrastructure Setup",   "deadline_days": 2 },
    { "title": "Authentication System",               "deadline_days": 4 },
    { "title": "Landing Page UI",                     "deadline_days": 5 },
    { "title": "Stripe Payment Integration",          "deadline_days": 5 },
    { "title": "Admin Dashboard & Analytics",         "deadline_days": 6 },
    { "title": "Testing & Deployment",                "deadline_days": 3 }
  ]
}
```

> **Without an AI key:** A fallback 4-milestone generic roadmap is used instead.

---

### Step 2: Employer Funds the Escrow

After reviewing the AI-generated roadmap, the employer deposits the project budget into the **Escrow Account**.

**What happens:**
- An `EscrowAccount` is created and linked to the project
- The deposited funds are **split equally across all milestones**
- Each milestone gets a `locked_amount` (e.g. $5,000 ÷ 6 milestones = ~$833 per milestone)
- A `deposit` transaction is recorded in the ledger
- The project status changes to `active`

The funds are **locked** — they cannot be withdrawn freely. They can only be released after AI verification or refunded in a dispute.

---

### Step 3: Employer Assigns a Freelancer

The employer finds a freelancer (by their username or PFI score) and assigns them to the project via the API or dashboard.

**What happens:**
- `freelancer_id` is set on the project
- Project status changes to `in_progress`
- The freelancer can now see the project and its milestones in their dashboard

---

### Step 4: Freelancer Works & Submits

The freelancer works on milestone #1. When done, they open the project page and click **Submit Work** on that milestone.

They fill in:
- **Submission type**: `code`, `content`, `design`, or `link`
- **GitHub repo URL** (for code projects)
- **Description or content** (for content/design projects)
- **Notes** for the reviewer

**What happens:**
- A `Submission` record is created in the database
- The milestone status changes to `submitted`
- The employer is notified (visually on their dashboard)

---

### Step 5: AI Evaluates the Submission

The employer clicks **Run AI Evaluation** on the submitted milestone. This triggers the **Automated Quality Assurance (AQA) Engine**.

The engine routes to different evaluators based on submission type:

#### For Code Submissions:

**Phase 1 — Docker Sandbox Testing**
- The system clones the GitHub repository into a temporary directory
- It detects the project type (Python, Node.js, Go, Java/Maven)
- It spins up an isolated Docker container with:
  - No network access (`--network none`)
  - Read-only filesystem
  - 256MB RAM limit
  - 30-second timeout
- It installs dependencies and runs the test suite (`pytest`, `jest`, `go test`, `mvn test`)
- Results (pass/fail, test count) are recorded

**Phase 2 — LLM Code Review**
- The repo URL and milestone description are sent to GPT-4o/Claude
- The AI acts as a senior code reviewer
- It checks against the acceptance criteria
- Returns structured JSON:

```json
{
  "completion_status": "complete",
  "confidence_score": 0.91,
  "quality_score": 0.88,
  "feedback": "Authentication implemented correctly with JWT. Missing rate limiting on login endpoint.",
  "issues": [
    { "severity": "minor", "description": "No rate limiting on /auth/login" }
  ],
  "positives": ["JWT implementation is secure", "Tests cover 80% of auth flows"]
}
```

**Phase 3 — Score Blending**
- If Docker tests passed → confidence score gets a +0.10 boost
- Final `confidence_score` determines the outcome

#### For Content Submissions:
- LLM evaluates against the milestone description using a rubric
- Scores: originality, relevance, clarity, completeness

#### For Design Submissions:
- Placeholder evaluation (returns 50% score, flags for manual review)

---

### Step 6: Automatic Payment Release

The evaluation result determines what happens next:

| Result | Action |
|---|---|
| `complete` + confidence ≥ 80% | Payment auto-released to freelancer |
| `complete` + confidence < 80% | Milestone marked `under_review`, employer decides |
| `partial` | Milestone marked `under_review`, feedback shown |
| `failed` | Milestone marked `rejected`, freelancer must resubmit |

**When payment releases:**
1. Platform fee is deducted (default 5%)
2. Remaining amount is credited to freelancer
3. `release` transaction recorded in ledger
4. Milestone status → `paid`
5. Freelancer's PFI score is updated

**Example for a $833 milestone:**
- Platform fee (5%): $41.65
- Freelancer receives: $791.35

---

### Step 7: PFI Score Updates

After every milestone evaluation, the freelancer's **Professional Fidelity Index (PFI)** is recalculated.

**The Formula:**
```
PFI = (0.40 × milestone_success_rate
     + 0.30 × average_quality_score
     + 0.20 × deadline_adherence_rate
     + 0.10 × (1 − dispute_rate)) × 550 + 300
```

**Score Range: 300 → 850**

| Range | Label | Meaning |
|---|---|---|
| 750 – 850 | Excellent | Top-tier freelancer, consistent delivery |
| 600 – 749 | Good | Reliable with minor issues |
| 450 – 599 | Average | Mixed track record |
| 300 – 449 | Developing | New or inconsistent |

Each update appends a history entry so employers can see the score trend over time.

---

## System Modules

### 1. Requirement Analysis Engine
**File:** [backend/app/ai/milestone_generator.py](../backend/app/ai/milestone_generator.py)

- Accepts a natural language project description
- Sends a structured prompt to GPT-4o or Claude
- Parses the JSON response into milestone records
- Falls back to a generic roadmap if AI is unavailable
- Supports all project types: web app, mobile, API, content, design, data science

---

### 2. Milestone Management API
**Files:** [backend/app/api/projects.py](../backend/app/api/projects.py), [backend/app/api/milestones.py](../backend/app/api/milestones.py)

Endpoints:
| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/projects/create` | Create project + auto-generate milestones |
| `GET` | `/projects/{id}` | Get project with all milestones |
| `GET` | `/projects/` | List all projects for current user |
| `POST` | `/projects/{id}/assign` | Assign freelancer to project |
| `POST` | `/milestones/submit` | Freelancer submits work |
| `POST` | `/milestones/evaluate` | Trigger AI evaluation |

---

### 3. Escrow Payment Engine
**File:** [backend/app/services/escrow_service.py](../backend/app/services/escrow_service.py)

- Simulates a wallet/escrow system using a PostgreSQL ledger
- Every financial action creates an immutable `Transaction` record
- Supported operations: `deposit`, `lock`, `release`, `refund`, `platform_fee`
- Safeguards: cannot release without evaluation, cannot double-release
- Platform fee is automatically deducted on release

**Transaction flow for a $1,000 milestone:**
```
DEPOSIT  +$1,000   (employer → escrow)
LOCK     -$1,000   (escrow → milestone hold)
RELEASE  +$950     (milestone hold → freelancer)
FEE      +$50      (milestone hold → platform)
```

---

### 4. Automated Quality Assurance Engine
**Files:** [backend/app/ai/qa_engine.py](../backend/app/ai/qa_engine.py), [backend/app/ai/code_evaluator.py](../backend/app/ai/code_evaluator.py)

Three evaluation pipelines:
1. **Code**: Docker sandbox → test execution → LLM review → blended score
2. **Content**: LLM rubric scoring (originality, clarity, relevance)
3. **Design**: Placeholder (manual review required)

All results are stored in the `evaluations` table with full JSON details.

---

### 5. Professional Fidelity Index (PFI)
**File:** [backend/app/services/pfi_service.py](../backend/app/services/pfi_service.py)

- Updated after every milestone event
- Tracks 4 metrics: success rate, quality, deadline adherence, dispute rate
- Uses a rolling average for quality score
- Stores full score history as JSONB for trend analysis
- Score range: 300–850 (similar to credit score scale for intuitive understanding)

---

### 6. Authentication & Security
**File:** [backend/app/utils/security.py](../backend/app/utils/security.py)

- JWT-based authentication (tokens expire in 24 hours)
- Passwords hashed with bcrypt
- Role-based access control: `employer`, `freelancer`, `admin`
- Route guards: employers can't submit work, freelancers can't trigger payments

---

## Database Schema

```
users
  └─ projects (employer_id, freelancer_id)
       └─ milestones
            └─ submissions (freelancer_id)
                 └─ evaluations
       └─ escrow_accounts
            └─ transactions (milestone_id)

users (freelancer)
  └─ reputation_scores
```

**8 tables total:**

| Table | Purpose |
|---|---|
| `users` | Accounts for employers, freelancers, admins |
| `projects` | Project metadata + AI roadmap (JSONB) |
| `milestones` | Individual deliverable units with escrow fields |
| `submissions` | Freelancer work submissions |
| `evaluations` | AI evaluation results with full JSON |
| `escrow_accounts` | Per-project escrow wallet |
| `transactions` | Immutable financial ledger |
| `reputation_scores` | PFI score + history per freelancer |

---

## Frontend Pages

| Page | Path | Who Uses It |
|---|---|---|
| Landing Page | `/` | Public |
| Register | `/auth/register` | New users (employer or freelancer) |
| Login | `/auth/login` | Returning users |
| Dashboard | `/dashboard` | Both — shows projects + PFI for freelancers |
| Create Project | `/projects/create` | Employer only |
| Project Detail | `/projects/[id]` | Both — milestones, escrow, submissions |

---

## Data Flow Diagram

```
EMPLOYER                    SYSTEM                       FREELANCER
   │                           │                               │
   │── POST /projects/create ──▶                               │
   │   { description, budget } │                               │
   │                    AI generates milestones                │
   │                    Milestones saved to DB                 │
   │◀─ project + milestones ───│                               │
   │                           │                               │
   │── POST /payments/deposit ─▶                               │
   │   { project_id, amount }  │                               │
   │                    Funds locked per milestone             │
   │◀─ escrow account ─────────│                               │
   │                           │                               │
   │── POST /projects/assign ──▶                               │
   │   { freelancer_id }       │                               │
   │                    Project → in_progress                  │
   │                           │── project visible ───────────▶│
   │                           │                               │
   │                           │◀─ POST /milestones/submit ────│
   │                           │   { repo_url, type, notes }   │
   │                    Submission saved                       │
   │                    Milestone → submitted                  │
   │                           │                               │
   │── POST /milestones/evaluate▶                              │
   │   { submission_id }       │                               │
   │                    QA Engine runs:                        │
   │                    1. Docker sandbox tests                │
   │                    2. LLM code review                     │
   │                    3. Score calculated                    │
   │                           │                               │
   │              if score ≥ 0.80:                             │
   │                    Payment released                       │
   │                    PFI score updated                      │
   │◀─ evaluation result ──────│──── payment notification ────▶│
```

---

## Configuration Reference

All settings are controlled via the `.env` file:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | JWT signing secret (generate with `openssl rand -hex 32`) |
| `DATABASE_URL` | postgres://... | PostgreSQL async connection string |
| `OPENAI_API_KEY` | — | For GPT-4o milestone generation & evaluation |
| `ANTHROPIC_API_KEY` | — | Alternative: Claude for AI features |
| `AI_MODEL` | `gpt-4o` | Which model to use |
| `PLATFORM_FEE_PERCENT` | `5.0` | Fee deducted on payment release |
| `SANDBOX_TIMEOUT_SECONDS` | `30` | Max time for Docker code execution |
| `DEBUG` | `false` | Enables SQL query logging |

---

## Running the Application

```bash
# Start everything
docker compose up --build

# Stop everything
docker compose down

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Reset database (WARNING: deletes all data)
docker compose down -v && docker compose up --build
```

**URLs:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

---

## What Works Without AI Keys

| Feature | Status |
|---|---|
| User registration & login | ✅ Fully works |
| Project creation | ✅ Uses fallback 4-milestone roadmap |
| Escrow deposit & locking | ✅ Fully works |
| Milestone submission | ✅ Fully works |
| AI evaluation | ⚠️ Returns 50% placeholder score |
| Auto payment release | ⚠️ Won't trigger (confidence < 80%) |
| PFI score tracking | ✅ Updates after manual approval |
| All dashboards | ✅ Fully works |

---

## Extending the Platform

| Feature | How to Add |
|---|---|
| Real payments | Integrate Stripe in `escrow_service.py` |
| Email notifications | Add SendGrid/Resend on milestone events |
| Dispute resolution | Wire `DISPUTE_ANALYSIS_PROMPT` to `POST /disputes/analyze` |
| Design evaluation | Implement vision API call in `qa_engine._evaluate_design()` |
| Freelancer search | Add `GET /users/freelancers?min_pfi=600` endpoint |
| Project marketplace | Change project listing to show all `active` projects |
