export type UserRole = 'employer' | 'freelancer' | 'admin'

export interface User {
  id: string
  email: string
  username: string
  full_name?: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface Milestone {
  id: string
  title: string
  description: string
  order_index: number
  deadline_days: number
  due_date?: string
  payment_amount: number
  status: 'pending' | 'in_progress' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'paid'
  release_status: 'locked' | 'released' | 'refunded'
  acceptance_criteria?: string[]
  deliverable_type?: string
  assigned_freelancer_id?: string
}

export interface Message {
  id: string
  project_id: string
  sender_id: string
  content: string
  message_type: 'user' | 'system'
  created_at: string
  sender: { id: string; username: string; role: string }
}

export interface Project {
  id: string
  title: string
  description: string
  project_type: string
  status: 'draft' | 'active' | 'in_progress' | 'completed' | 'disputed' | 'cancelled'
  total_budget: number
  employer_id: string
  freelancer_id?: string
  ai_roadmap?: any
  milestones: Milestone[]
  created_at: string
}

export interface Evaluation {
  id: string
  completion_status: 'complete' | 'partial' | 'failed'
  confidence_score: number
  quality_score?: number
  feedback?: string
  auto_approved: boolean
  created_at: string
}

export interface Submission {
  id: string
  milestone_id: string
  submission_type: string
  content?: string
  repo_url?: string
  notes?: string
  created_at: string
  evaluation?: Evaluation
}

export interface EscrowAccount {
  id: string
  project_id: string
  total_deposited: number
  locked_balance: number
  released_balance: number
  refunded_balance: number
}

export interface ReputationScore {
  user_id: string
  pfi_score: number
  milestone_success_rate: number
  avg_quality_score: number
  deadline_adherence_rate: number
  dispute_rate: number
  total_milestones: number
  successful_milestones: number
  score_history: any[]
  updated_at: string
}

export interface Application {
  id: string
  project_id: string
  freelancer_id: string
  cover_letter?: string
  proposed_rate?: number
  status: 'pending' | 'accepted' | 'rejected' | 'withdrawn'
  employer_note?: string
  created_at: string
  freelancer?: {
    id: string
    username: string
    full_name?: string
    email: string
  }
}
