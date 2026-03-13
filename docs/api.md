# Bitlance API Reference

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

All protected endpoints require:
```
Authorization: Bearer <token>
```

## Authentication

### POST /auth/register
Register a new user (employer or freelancer).

**Request:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123!",
  "role": "employer",
  "full_name": "John Doe"
}
```

**Response 201:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "...", "role": "employer", ... }
}
```

---

### POST /auth/login
Authenticate and get a JWT token.

**Request:**
```json
{ "email": "user@example.com", "password": "SecurePass123!" }
```

---

## Projects

### POST /projects/create *(employer only)*
AI decomposes description into milestones automatically.

**Request:**
```json
{
  "title": "SaaS Landing Page",
  "description": "Build a landing page with Stripe integration and user auth.",
  "total_budget": 5000.00,
  "project_type": "web_application"
}
```

**Response 201:** Full project with AI-generated milestones.

### GET /projects/{id}
Get project details including milestones.

### GET /projects/
List all projects for current user.

---

## Milestones

### POST /milestones/submit *(freelancer only)*
Submit work for a milestone.

**Request:**
```json
{
  "milestone_id": "uuid",
  "submission_type": "code",
  "repo_url": "https://github.com/user/repo",
  "notes": "All tests passing."
}
```

### POST /milestones/evaluate *(employer/admin)*
Trigger AI quality evaluation for a submission.

**Request:**
```json
{ "submission_id": "uuid" }
```

**Response:** Evaluation result with auto-payment if approved.

---

## Payments

### POST /payments/deposit *(employer only)*
Deposit funds into project escrow.

**Request:**
```json
{ "project_id": "uuid", "amount": 5000.00 }
```

### POST /payments/release
Manually release a milestone payment (requires prior AI approval).

### GET /payments/escrow/{project_id}
Get escrow account status.

### GET /payments/transactions/{project_id}
Get transaction ledger for a project.

---

## Reputation

### GET /reputation/{freelancer_id}
Get PFI score and history for a freelancer.

**Response:**
```json
{
  "pfi_score": 742.5,
  "milestone_success_rate": 0.92,
  "avg_quality_score": 0.88,
  "deadline_adherence_rate": 0.85,
  "dispute_rate": 0.02,
  "total_milestones": 24
}
```
