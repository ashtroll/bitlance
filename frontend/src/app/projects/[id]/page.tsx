'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { projectsApi, milestonesApi, paymentsApi } from '@/lib/api'
import type { Project, Milestone, User, EscrowAccount } from '@/lib/types'

const statusColor: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-500',
  in_progress: 'bg-amber-100 text-amber-700',
  submitted: 'bg-blue-100 text-blue-700',
  under_review: 'bg-purple-100 text-purple-700',
  approved: 'bg-teal-100 text-teal-700',
  rejected: 'bg-red-100 text-red-700',
  paid: 'bg-green-100 text-green-700',
}

function MilestoneCard({ m, user, projectId, onRefresh }: {
  m: Milestone; user: User; projectId: string; onRefresh: () => void
}) {
  const [submitting, setSubmitting] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [form, setForm] = useState({ type: 'code', repo_url: '', content: '', notes: '' })
  const [showForm, setShowForm] = useState(false)

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await milestonesApi.submit({
        milestone_id: m.id,
        submission_type: form.type,
        repo_url: form.repo_url || undefined,
        content: form.content || undefined,
        notes: form.notes,
      })
      toast.success('Submission sent!')
      setShowForm(false)
      onRefresh()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEvaluate = async (submissionId: string) => {
    setEvaluating(true)
    try {
      const { data } = await milestonesApi.evaluate({ submission_id: submissionId })
      toast.success(`Evaluation: ${data.completion_status} (${Math.round(data.confidence_score * 100)}% confidence)`)
      onRefresh()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Evaluation failed')
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className={`bg-white rounded-xl border-2 p-5 ${m.status === 'paid' ? 'border-green-200' : 'border-slate-200'}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="font-semibold text-slate-900">{m.title}</h4>
          <p className="text-sm text-slate-500 mt-0.5">{m.description}</p>
        </div>
        <div className="text-right ml-4">
          <div className="font-bold text-slate-900">${m.payment_amount.toFixed(2)}</div>
          <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor[m.status]}`}>
            {m.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      <div className="flex gap-2 text-xs text-slate-400">
        <span>{m.deadline_days} days</span>
        <span>·</span>
        <span className={m.release_status === 'released' ? 'text-green-600' : 'text-slate-400'}>
          {m.release_status === 'released' ? '✓ Paid' : m.release_status === 'refunded' ? '↩ Refunded' : '🔒 Locked'}
        </span>
      </div>

      {/* Freelancer submit button */}
      {user.role === 'freelancer' && ['pending', 'in_progress', 'rejected'].includes(m.status) && (
        <div className="mt-4">
          {!showForm ? (
            <button onClick={() => setShowForm(true)}
              className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-500 transition">
              Submit Work
            </button>
          ) : (
            <div className="space-y-3 mt-2 border-t border-slate-100 pt-3">
              <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                {['code', 'content', 'design', 'link'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input value={form.repo_url} onChange={e => setForm({ ...form, repo_url: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                placeholder="GitHub repo URL (for code)" />
              <textarea rows={3} value={form.content} onChange={e => setForm({ ...form, content: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm resize-none"
                placeholder="Description or content..." />
              <textarea rows={2} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm resize-none"
                placeholder="Notes for reviewer..." />
              <div className="flex gap-2">
                <button onClick={handleSubmit} disabled={submitting}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-500 transition disabled:opacity-50">
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
                <button onClick={() => setShowForm(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-600">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Employer evaluate button */}
      {user.role === 'employer' && m.status === 'submitted' && (
        <button
          onClick={() => {/* need submission id - simplified here */ toast.error('Use the evaluate API endpoint directly')}}
          disabled={evaluating}
          className="mt-4 text-sm bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition disabled:opacity-50">
          {evaluating ? 'Evaluating...' : 'Run AI Evaluation'}
        </button>
      )}
    </div>
  )
}

export default function ProjectPage() {
  const params = useParams()
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [escrow, setEscrow] = useState<EscrowAccount | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const id = params.id as string
    const [projRes, escrowRes] = await Promise.allSettled([
      projectsApi.get(id),
      paymentsApi.getEscrow(id),
    ])
    if (projRes.status === 'fulfilled') setProject(projRes.value.data)
    if (escrowRes.status === 'fulfilled') setEscrow(escrowRes.value.data)
    setLoading(false)
  }

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (!stored) { router.push('/auth/login'); return }
    setUser(JSON.parse(stored))
    load()
  }, [params.id])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
    </div>
  )

  if (!project || !user) return null

  const completedMilestones = project.milestones.filter(m => m.status === 'paid').length
  const progress = project.milestones.length > 0
    ? Math.round((completedMilestones / project.milestones.length) * 100) : 0

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <Link href="/dashboard" className="text-blue-600 text-sm">← Dashboard</Link>
        <span className="text-slate-800 font-semibold">{project.title}</span>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{project.title}</h1>
              <p className="text-slate-500 text-sm mt-1">{project.description}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-slate-900">${project.total_budget.toLocaleString()}</div>
              <span className="text-sm text-slate-500 capitalize">{project.status.replace('_', ' ')}</span>
            </div>
          </div>

          {/* Progress */}
          <div className="mt-5">
            <div className="flex justify-between text-xs text-slate-500 mb-1.5">
              <span>{completedMilestones}/{project.milestones.length} milestones complete</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full transition-all" style={{ width: `${progress}%` }}></div>
            </div>
          </div>
        </div>

        {/* Escrow Panel */}
        {escrow && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
            <h2 className="font-semibold text-slate-900 mb-4">Escrow Account</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Total Deposited', value: `$${escrow.total_deposited.toFixed(2)}`, color: 'text-slate-900' },
                { label: 'Locked', value: `$${escrow.locked_balance.toFixed(2)}`, color: 'text-amber-600' },
                { label: 'Released', value: `$${escrow.released_balance.toFixed(2)}`, color: 'text-green-600' },
                { label: 'Refunded', value: `$${escrow.refunded_balance.toFixed(2)}`, color: 'text-slate-400' },
              ].map(item => (
                <div key={item.label} className="text-center">
                  <div className={`text-xl font-bold ${item.color}`}>{item.value}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Milestones */}
        <h2 className="font-semibold text-slate-900 mb-4">Milestones</h2>
        <div className="space-y-4">
          {project.milestones
            .sort((a, b) => a.order_index - b.order_index)
            .map(m => (
              <MilestoneCard key={m.id} m={m} user={user} projectId={project.id} onRefresh={load} />
            ))}
        </div>
      </div>
    </div>
  )
}
