# ⚡ Bitlance — Autonomous AI Payment & Project Agent

An intelligent intermediary platform between employers and freelancers that:
- **Auto-decomposes** project descriptions into verifiable milestones using AI
- **Holds payments in escrow** locked per milestone
- **Verifies deliverables** using AI evaluation + Docker sandbox test execution
- **Auto-releases payments** when confidence ≥ 80%
- **Scores freelancers** via the Professional Fidelity Index (PFI, 300–850)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                  │
│  Employer Dashboard  │  Freelancer Dashboard  │  Auth    │
└──────────────────────────────┬──────────────────────────┘
                               │ HTTP/REST
┌──────────────────────────────▼──────────────────────────┐
│                     BACKEND (FastAPI)                     │
│                                                           │
│  /auth  /projects  /milestones  /payments  /reputation   │
│                                                           │
│  ┌───────────────┐  ┌─────────────────┐  ┌───────────┐  │
│  │  Milestone    │  │   QA Engine     │  │  Escrow   │  │
│  │  Generator   │  │  (LLM + Docker) │  │  Service  │  │
│  │  (LLM Chain)  │  └────────┬────────┘  └─────┬─────┘  │
│  └───────┬───────┘           │                  │        │
│          │            ┌──────▼──────┐    ┌──────▼─────┐ │
│          │            │   Docker    │    │    PFI     │ │
│          │            │   Sandbox   │    │   Scoring  │ │
│          │            └─────────────┘    └────────────┘ │
└──────────┼──────────────────────────────────────────────┘
           │
┌──────────▼──────────┐
│   PostgreSQL 16     │
│  users, projects,   │
│  milestones, escrow,│
│  evaluations, PFI   │
└─────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI or Anthropic API key

### 1. Clone & Configure

```bash
git clone <repo-url> bitlance
cd bitlance
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### 2. Start Everything

```bash
docker compose up --build
```

Services:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### 3. Seed Test Data

```bash
bash infra/scripts/seed.sh
```

This creates:
- **employer@test.com** / `Password123!` (employer)
- **freelancer@test.com** / `Password123!` (freelancer)

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Start PostgreSQL locally (or use Docker just for DB)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password -e POSTGRES_DB=bitlance postgres:16-alpine

# Copy and configure env
cp .env.example .env

# Start API
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Project Structure

```
bitlance/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── api/                 # Route handlers
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── milestones.py
│   │   │   ├── payments.py
│   │   │   └── reputation.py
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic
│   │   │   ├── escrow_service.py
│   │   │   └── pfi_service.py
│   │   ├── ai/                  # AI modules
│   │   │   ├── milestone_generator.py
│   │   │   ├── qa_engine.py
│   │   │   ├── code_evaluator.py
│   │   │   └── prompts.py
│   │   └── utils/
│   │       └── security.py      # JWT auth helpers
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router pages
│       └── lib/                 # API client & types
├── infra/
│   ├── sql/init.sql             # Full DB schema
│   └── scripts/
├── docs/api.md
└── docker-compose.yml
```

---

## Core Flows

### 1. Project Creation (Employer)
1. Employer submits project description + budget
2. AI (GPT-4o/Claude) decomposes into 3–8 milestones
3. Milestones stored with acceptance criteria
4. Employer deposits funds → locked in escrow per milestone

### 2. Milestone Submission (Freelancer)
1. Freelancer submits work (repo URL, content, etc.)
2. Milestone status → `submitted`

### 3. Automated Evaluation
1. Employer triggers evaluation
2. QA Engine runs:
   - **Code**: Docker sandbox tests + LLM review
   - **Content**: LLM rubric scoring
3. Returns `{ completion_status, confidence_score, feedback }`
4. If `complete` + confidence ≥ 80% → payment auto-released
5. PFI score updated for freelancer

### 4. PFI Formula

```
PFI = (0.40 × success_rate
     + 0.30 × avg_quality_score
     + 0.20 × deadline_adherence
     + 0.10 × (1 − dispute_rate)) × 550 + 300

Range: 300 (worst) → 850 (perfect)
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | One of these | OpenAI API key |
| `ANTHROPIC_API_KEY` | One of these | Anthropic Claude API key |
| `AI_MODEL` | No | Default: `gpt-4o` |
| `SECRET_KEY` | Yes | JWT signing secret |
| `DATABASE_URL` | Yes | PostgreSQL async URL |
| `PLATFORM_FEE_PERCENT` | No | Default: `5.0` |

---

## Deployment (Render / Railway)

### Render

1. Create a **PostgreSQL** database on Render
2. Create a **Web Service** pointing to `/backend`, build command: `pip install -r requirements.txt`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Create a second **Web Service** for `/frontend`, build: `npm install && npm run build`, start: `npm start`
4. Set environment variables from `.env.example`

### Railway

```bash
railway login
railway init
railway add postgresql
railway up
```

---

## Manual Tasks for Developer

See the **Manual Tasks** section at the bottom for what you must configure yourself.

---

## Security Notes

- JWT tokens expire after 24 hours (configurable)
- Docker sandbox runs with `--network none`, `--read-only`, `--memory 256m`
- Escrow funds never released without AI verification
- Role-based access: employers create/fund, freelancers submit, both can view

---

## License

MIT — built as an MVP prototype. Not production-ready for real financial transactions without proper payment provider integration.
