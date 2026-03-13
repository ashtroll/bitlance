-- Bitlance Database Schema
-- PostgreSQL 16+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- USERS
-- ============================================================
CREATE TYPE user_role AS ENUM ('employer', 'freelancer', 'admin');

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================
-- PROJECTS
-- ============================================================
CREATE TYPE project_status AS ENUM ('draft', 'active', 'in_progress', 'completed', 'disputed', 'cancelled');
CREATE TYPE project_type AS ENUM ('web_application', 'mobile_app', 'api', 'content', 'design', 'data_science', 'other');

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    project_type project_type NOT NULL DEFAULT 'other',
    status project_status DEFAULT 'draft',
    total_budget DECIMAL(12,2) NOT NULL,
    employer_id UUID NOT NULL REFERENCES users(id),
    freelancer_id UUID REFERENCES users(id),
    ai_roadmap JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_employer ON projects(employer_id);
CREATE INDEX idx_projects_freelancer ON projects(freelancer_id);
CREATE INDEX idx_projects_status ON projects(status);

-- ============================================================
-- MILESTONES
-- ============================================================
CREATE TYPE milestone_status AS ENUM ('pending', 'in_progress', 'submitted', 'under_review', 'approved', 'rejected', 'paid');

CREATE TABLE IF NOT EXISTS milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    deadline_days INTEGER NOT NULL,
    due_date DATE,
    payment_amount DECIMAL(12,2) NOT NULL,
    locked_amount DECIMAL(12,2) DEFAULT 0,
    status milestone_status DEFAULT 'pending',
    release_status VARCHAR(20) DEFAULT 'locked' CHECK (release_status IN ('locked', 'released', 'refunded')),
    payment_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_milestones_project ON milestones(project_id);
CREATE INDEX idx_milestones_status ON milestones(status);

-- ============================================================
-- SUBMISSIONS
-- ============================================================
CREATE TYPE submission_type AS ENUM ('code', 'content', 'design', 'link');

CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    freelancer_id UUID NOT NULL REFERENCES users(id),
    submission_type submission_type NOT NULL,
    content TEXT,
    repo_url VARCHAR(500),
    file_paths JSONB DEFAULT '[]',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_submissions_milestone ON submissions(milestone_id);
CREATE INDEX idx_submissions_freelancer ON submissions(freelancer_id);

-- ============================================================
-- EVALUATIONS
-- ============================================================
CREATE TYPE completion_status AS ENUM ('complete', 'partial', 'failed');

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    completion_status completion_status NOT NULL,
    confidence_score DECIMAL(4,3) NOT NULL,
    quality_score DECIMAL(4,3),
    feedback TEXT,
    test_results JSONB,
    llm_review JSONB,
    auto_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_evaluations_milestone ON evaluations(milestone_id);
CREATE INDEX idx_evaluations_submission ON evaluations(submission_id);

-- ============================================================
-- ESCROW ACCOUNTS
-- ============================================================
CREATE TABLE IF NOT EXISTS escrow_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    total_deposited DECIMAL(12,2) DEFAULT 0,
    locked_balance DECIMAL(12,2) DEFAULT 0,
    released_balance DECIMAL(12,2) DEFAULT 0,
    refunded_balance DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_escrow_project ON escrow_accounts(project_id);
CREATE INDEX idx_escrow_user ON escrow_accounts(user_id);

-- ============================================================
-- TRANSACTIONS
-- ============================================================
CREATE TYPE transaction_type AS ENUM ('deposit', 'lock', 'release', 'refund', 'platform_fee');
CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'failed', 'reversed');

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    escrow_account_id UUID NOT NULL REFERENCES escrow_accounts(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES milestones(id),
    transaction_type transaction_type NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    status transaction_status DEFAULT 'pending',
    reference_id VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_escrow ON transactions(escrow_account_id);
CREATE INDEX idx_transactions_milestone ON transactions(milestone_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);

-- ============================================================
-- REPUTATION SCORES (PFI)
-- ============================================================
CREATE TABLE IF NOT EXISTS reputation_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    pfi_score DECIMAL(6,1) DEFAULT 500.0,
    milestone_success_rate DECIMAL(4,3) DEFAULT 0,
    avg_quality_score DECIMAL(4,3) DEFAULT 0,
    deadline_adherence_rate DECIMAL(4,3) DEFAULT 0,
    dispute_rate DECIMAL(4,3) DEFAULT 0,
    total_milestones INTEGER DEFAULT 0,
    successful_milestones INTEGER DEFAULT 0,
    disputed_milestones INTEGER DEFAULT 0,
    on_time_milestones INTEGER DEFAULT 0,
    score_history JSONB DEFAULT '[]',
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reputation_user ON reputation_scores(user_id);
CREATE INDEX idx_reputation_pfi ON reputation_scores(pfi_score DESC);

-- ============================================================
-- TRIGGERS: updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_milestones_updated_at BEFORE UPDATE ON milestones FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_escrow_updated_at BEFORE UPDATE ON escrow_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_reputation_updated_at BEFORE UPDATE ON reputation_scores FOR EACH ROW EXECUTE FUNCTION update_updated_at();
