'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { projectsApi, milestonesApi, paymentsApi } from '@/lib/api'
import type { Project, Milestone, User, EscrowAccount, Application, Submission, Message } from '@/lib/types'

// ─── Status helpers ──────────────────────────────────────────────────────────
const milestoneStatusStyle: Record<string, string> = {
  pending:      'bg-slate-100 text-slate-500',
  in_progress:  'bg-amber-100 text-amber-700',
  submitted:    'bg-blue-100 text-blue-700',
  under_review: 'bg-purple-100 text-purple-700',
  approved:     'bg-teal-100 text-teal-700',
  rejected:     'bg-red-100 text-red-700',
  paid:         'bg-green-100 text-green-700',
}

const appStatusStyle: Record<string, string> = {
  pending:   'bg-amber-100 text-amber-700',
  accepted:  'bg-green-100 text-green-700',
  rejected:  'bg-red-100 text-red-700',
  withdrawn: 'bg-slate-100 text-slate-500',
}

// ─── Milestone Card ───────────────────────────────────────────────────────────
function MilestoneCard({
  m, user, projectId, acceptedFreelancers, onRefresh,
}: { m: Milestone; user: User; projectId: string; acceptedFreelancers: Application[]; onRefresh: () => void }) {
  const [showSubmitForm, setShowSubmitForm] = useState(false)
  const [showSubmissions, setShowSubmissions] = useState(false)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loadingSubmissions, setLoadingSubmissions] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ type: 'code', repo_url: '', content: '', notes: '' })

  const loadSubmissions = async () => {
    setLoadingSubmissions(true)
    try {
      const { data } = await milestonesApi.getSubmissions(m.id)
      setSubmissions(data)
    } catch {
      toast.error('Failed to load submissions')
    } finally {
      setLoadingSubmissions(false)
    }
  }

  const handleShowSubmissions = () => {
    setShowSubmissions(v => !v)
    if (!showSubmissions) loadSubmissions()
  }

  const handleSubmit = async () => {
    if (!form.repo_url && !form.content) {
      toast.error('Provide a repo URL or content description')
      return
    }
    setSubmitting(true)
    try {
      await milestonesApi.submit({
        milestone_id: m.id,
        submission_type: form.type,
        repo_url: form.repo_url || undefined,
        content: form.content || undefined,
        notes: form.notes || undefined,
      })
      toast.success('Work submitted successfully!')
      setShowSubmitForm(false)
      setForm({ type: 'code', repo_url: '', content: '', notes: '' })
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
      const pct = Math.round(data.confidence_score * 100)
      const icon = data.completion_status === 'complete' ? '✅' : data.completion_status === 'partial' ? '⚠️' : '❌'
      toast.success(`${icon} ${data.completion_status} — ${pct}% confidence`)
      await loadSubmissions()
      onRefresh()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Evaluation failed')
    } finally {
      setEvaluating(false)
    }
  }

  const canSubmit = user.role === 'freelancer' &&
    ['pending', 'in_progress', 'rejected'].includes(m.status)
  const canViewSubmissions = m.status !== 'pending' &&
    (user.role === 'employer' || user.role === 'freelancer')

  return (
    <div className={`bg-white rounded-xl border-2 p-5 transition-all ${
      m.status === 'paid' ? 'border-green-200 bg-green-50/30' :
      m.status === 'rejected' ? 'border-red-100' : 'border-slate-200'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-6 h-6 bg-slate-100 text-slate-600 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
              {m.order_index + 1}
            </span>
            <h4 className="font-semibold text-slate-900 truncate">{m.title}</h4>
          </div>
          <p className="text-sm text-slate-500 leading-relaxed ml-8">{m.description}</p>

          {/* Acceptance criteria */}
          {m.acceptance_criteria && m.acceptance_criteria.length > 0 && (
            <div className="ml-8 mt-2">
              <p className="text-xs font-medium text-slate-400 mb-1">Acceptance Criteria</p>
              <ul className="space-y-0.5">
                {m.acceptance_criteria.map((c, i) => (
                  <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                    <span className="text-blue-400 mt-0.5">›</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="text-right flex-shrink-0">
          <div className="font-bold text-lg text-slate-900">${m.payment_amount.toFixed(2)}</div>
          <span className={`inline-block text-xs px-2 py-0.5 rounded-full mt-1 ${milestoneStatusStyle[m.status]}`}>
            {m.status.replace(/_/g, ' ')}
          </span>
          <div className="text-xs text-slate-400 mt-1">
            {m.due_date ? `Due ${new Date(m.due_date).toLocaleDateString()}` : `${m.deadline_days}d`}
          </div>
        </div>
      </div>

      {/* Assigned freelancer + assignment UI for employer */}
      {user.role === 'employer' && acceptedFreelancers.length > 0 && (
        <div className="mt-3 ml-8 flex items-center gap-2">
          {m.assigned_freelancer_id ? (
            <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-2.5 py-1 rounded-full">
              Assigned: {acceptedFreelancers.find(a => a.freelancer_id === m.assigned_freelancer_id)?.freelancer?.username || 'freelancer'}
            </span>
          ) : (
            <select
              defaultValue=""
              onChange={async e => {
                if (!e.target.value) return
                try {
                  await projectsApi.assignMilestoneFreelancer(projectId, m.id, e.target.value)
                  toast.success('Freelancer assigned to milestone')
                  onRefresh()
                } catch (err: any) {
                  toast.error(err.response?.data?.detail || 'Assignment failed')
                }
              }}
              className="text-xs border border-slate-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500">
              <option value="">Assign freelancer to this milestone…</option>
              {acceptedFreelancers.map(a => (
                <option key={a.freelancer_id} value={a.freelancer_id}>
                  {a.freelancer?.username || a.freelancer_id}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Payment status bar */}
      <div className={`mt-3 flex items-center gap-1.5 text-xs ${
        m.release_status === 'released' ? 'text-green-600' :
        m.release_status === 'refunded' ? 'text-slate-400' : 'text-amber-600'
      }`}>
        <span>{m.release_status === 'released' ? '✓ Payment released' :
               m.release_status === 'refunded' ? '↩ Refunded' : '🔒 Funds locked'}</span>
      </div>

      {/* Freelancer: Submit Work */}
      {canSubmit && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          {!showSubmitForm ? (
            <button onClick={() => setShowSubmitForm(true)}
              className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-500 transition font-medium">
              Submit Work
            </button>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Deliverable Type</label>
                  <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {['code', 'content', 'design', 'link'].map(t => (
                      <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Repository / URL</label>
                  <input value={form.repo_url} onChange={e => setForm({ ...form, repo_url: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="https://github.com/..." />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Description / Content</label>
                <textarea rows={3} value={form.content}
                  onChange={e => setForm({ ...form, content: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  placeholder="Describe what you've completed..." />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Notes for Reviewer</label>
                <textarea rows={2} value={form.notes}
                  onChange={e => setForm({ ...form, notes: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  placeholder="Any context the reviewer should know..." />
              </div>
              <div className="flex gap-2">
                <button onClick={handleSubmit} disabled={submitting}
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-500 transition disabled:opacity-50">
                  {submitting ? 'Submitting...' : 'Submit for Review'}
                </button>
                <button onClick={() => setShowSubmitForm(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 transition">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Employer: View Submissions + Evaluate */}
      {canViewSubmissions && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <button onClick={handleShowSubmissions}
            className="text-sm text-blue-600 font-medium hover:underline">
            {showSubmissions ? 'Hide' : 'View'} Submissions {submissions.length > 0 ? `(${submissions.length})` : ''}
          </button>

          {showSubmissions && (
            <div className="mt-3 space-y-3">
              {loadingSubmissions && (
                <div className="text-sm text-slate-400">Loading submissions...</div>
              )}
              {!loadingSubmissions && submissions.length === 0 && (
                <div className="text-sm text-slate-400">No submissions yet.</div>
              )}
              {submissions.map((sub) => (
                <div key={sub.id} className="border border-slate-200 rounded-lg p-4 bg-slate-50">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                        <span className="capitalize">{sub.submission_type}</span>
                        <span className="text-slate-400">·</span>
                        <span className="text-slate-400 text-xs">{new Date(sub.created_at).toLocaleString()}</span>
                      </div>
                      {sub.repo_url && (
                        <a href={sub.repo_url} target="_blank" rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline break-all mt-1 block">
                          {sub.repo_url}
                        </a>
                      )}
                      {sub.content && (
                        <p className="text-xs text-slate-600 mt-1">{sub.content}</p>
                      )}
                      {sub.notes && (
                        <p className="text-xs text-slate-400 mt-1 italic">{sub.notes}</p>
                      )}

                      {/* Evaluation Report */}
                      {sub.evaluation && (
                        <div className={`mt-3 rounded-xl border overflow-hidden text-xs ${
                          sub.evaluation.completion_status === 'complete' ? 'border-green-200' :
                          sub.evaluation.completion_status === 'partial' ? 'border-amber-200' : 'border-red-200'
                        }`}>
                          {/* Header */}
                          <div className={`px-3 py-2 flex items-center justify-between ${
                            sub.evaluation.completion_status === 'complete' ? 'bg-green-50' :
                            sub.evaluation.completion_status === 'partial' ? 'bg-amber-50' : 'bg-red-50'
                          }`}>
                            <span className="font-bold text-sm flex items-center gap-1.5">
                              {sub.evaluation.completion_status === 'complete' ? '✅' :
                               sub.evaluation.completion_status === 'partial' ? '⚠️' : '❌'}
                              <span className="capitalize">{sub.evaluation.completion_status}</span>
                              {sub.evaluation.auto_approved && (
                                <span className="text-xs bg-white/70 border px-1.5 py-0.5 rounded-full font-normal ml-1">Auto-approved</span>
                              )}
                            </span>
                            <div className="flex gap-3 font-semibold">
                              <span>Confidence: {Math.round(sub.evaluation.confidence_score * 100)}%</span>
                              {sub.evaluation.quality_score != null && (
                                <span>Quality: {Math.round(sub.evaluation.quality_score * 100)}%</span>
                              )}
                            </div>
                          </div>
                          {/* Score bars */}
                          <div className="px-3 py-2 bg-white space-y-1.5">
                            {[
                              { label: 'Confidence', v: sub.evaluation.confidence_score, c: 'bg-blue-500' },
                              { label: 'Quality', v: sub.evaluation.quality_score ?? sub.evaluation.confidence_score, c: 'bg-purple-500' },
                            ].map(b => (
                              <div key={b.label} className="flex items-center gap-2">
                                <span className="w-20 text-slate-400 shrink-0">{b.label}</span>
                                <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                  <div className={`h-full ${b.c} rounded-full`} style={{ width: `${(b.v || 0) * 100}%` }} />
                                </div>
                                <span className="w-8 text-right text-slate-600">{Math.round((b.v || 0) * 100)}%</span>
                              </div>
                            ))}
                          </div>
                          {/* Feedback */}
                          {sub.evaluation.feedback && (
                            <div className="px-3 py-2 border-t border-slate-100 bg-slate-50 text-slate-600 leading-relaxed">
                              {sub.evaluation.feedback}
                            </div>
                          )}
                          {/* Criteria verification */}
                          {(sub.evaluation as any).llm_review?.criteria_results?.length > 0 && (
                            <div className="px-3 py-2 border-t border-slate-100 bg-white">
                              <p className="text-slate-400 font-semibold mb-1.5 uppercase tracking-wide" style={{fontSize:'10px'}}>Acceptance Criteria</p>
                              {((sub.evaluation as any).llm_review.criteria_results as any[]).map((cr: any, i: number) => (
                                <div key={i} className={`flex items-start gap-1.5 mb-1 ${cr.met ? 'text-green-700' : 'text-red-600'}`}>
                                  <span className="shrink-0 mt-0.5">{cr.met ? '✓' : '✗'}</span>
                                  <span>{cr.criterion}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex-shrink-0 flex flex-col gap-1.5">
                      {user.role === 'employer' && (
                        <button onClick={() => handleEvaluate(sub.id)} disabled={evaluating}
                          className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded-lg hover:bg-purple-500 transition disabled:opacity-50 font-medium">
                          {evaluating ? 'Evaluating…' : sub.evaluation ? 'Re-evaluate' : 'Evaluate'}
                        </button>
                      )}
                      {sub.evaluation && sub.evaluation.completion_status !== 'complete' && (
                        <button
                          onClick={async () => {
                            const concern = window.prompt('Describe your concern with this evaluation:')
                            if (!concern?.trim()) return
                            try {
                              await milestonesApi.raiseDispute({ submission_id: sub.id, concern })
                              toast.success('Dispute filed — AI arbitration posted to discussion')
                              await loadSubmissions()
                            } catch (err: any) {
                              toast.error(err.response?.data?.detail || 'Dispute failed')
                            }
                          }}
                          className="text-xs border border-red-200 text-red-600 px-3 py-1.5 rounded-lg hover:bg-red-50 transition font-medium">
                          Raise Dispute
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Discussion Panel ─────────────────────────────────────────────────────────
function DiscussionPanel({ projectId, user }: { projectId: string; user: User }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await projectsApi.getMessages(projectId)
      setMessages(data)
    } catch { /* project may have no messages yet */ }
  }, [projectId])

  useEffect(() => { load() }, [load])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim()) return
    setSending(true)
    try {
      await projectsApi.sendMessage(projectId, text.trim())
      setText('')
      await load()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to send')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 mb-6">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <h2 className="font-semibold text-slate-900">Discussion</h2>
        <button onClick={load} className="text-xs text-slate-400 hover:text-slate-600">Refresh</button>
      </div>

      <div className="px-6 py-4 max-h-80 overflow-y-auto space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-6">No messages yet. Start the conversation.</p>
        )}
        {messages.map(msg => {
          const isMe = msg.sender_id === user.id
          const isSystem = msg.message_type === 'system'
          if (isSystem) {
            return (
              <div key={msg.id} className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-xs text-slate-600 whitespace-pre-wrap">
                <span className="font-medium text-slate-400 block mb-1">AI System</span>
                {msg.content}
              </div>
            )
          }
          return (
            <div key={msg.id} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                isMe ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800'
              }`}>
                {!isMe && (
                  <div className="text-xs font-medium mb-1 opacity-70">
                    {msg.sender.username} · {msg.sender.role}
                  </div>
                )}
                <p className="leading-relaxed">{msg.content}</p>
                <div className={`text-xs mt-1 opacity-60 ${isMe ? 'text-right' : ''}`}>
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSend} className="px-6 py-4 border-t border-slate-100 flex gap-3">
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Write a message…"
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button type="submit" disabled={sending || !text.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-500 transition disabled:opacity-50">
          {sending ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}

// ─── Applications Panel (Employer) ────────────────────────────────────────────
function ApplicationsPanel({ projectId, onRefresh }: { projectId: string; onRefresh: () => void }) {
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [reviewing, setReviewing] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { data } = await projectsApi.getApplications(projectId)
      setApplications(data)
    } catch {
      // No applications yet
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const handleReview = async (appId: string, status: 'accepted' | 'rejected', note?: string) => {
    setReviewing(appId)
    try {
      await projectsApi.reviewApplication(projectId, appId, { status, employer_note: note })
      toast.success(status === 'accepted' ? 'Freelancer assigned to project!' : 'Application rejected')
      await load()
      onRefresh()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Action failed')
    } finally {
      setReviewing(null)
    }
  }

  if (loading) return <div className="text-sm text-slate-400 py-4">Loading applications...</div>

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
      <h2 className="font-semibold text-slate-900 mb-4">
        Applicants <span className="text-slate-400 font-normal text-sm">({applications.length})</span>
      </h2>

      {applications.length === 0 ? (
        <p className="text-sm text-slate-400">No applications yet. Share your project link to attract freelancers.</p>
      ) : (
        <div className="space-y-3">
          {applications.map((app) => (
            <div key={app.id} className="border border-slate-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">
                      {(app.freelancer?.username || '?')[0].toUpperCase()}
                    </div>
                    <div>
                      <div className="font-medium text-slate-900 text-sm">
                        {app.freelancer?.full_name || app.freelancer?.username}
                      </div>
                      <div className="text-xs text-slate-400">@{app.freelancer?.username}</div>
                    </div>
                    <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${appStatusStyle[app.status]}`}>
                      {app.status}
                    </span>
                  </div>

                  {app.proposed_rate && (
                    <div className="mt-2 text-sm text-slate-600">
                      Proposed rate: <span className="font-semibold">${app.proposed_rate.toFixed(2)}</span>
                    </div>
                  )}

                  {app.cover_letter && (
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">{app.cover_letter}</p>
                  )}

                  {app.employer_note && (
                    <p className="mt-1 text-xs text-slate-400 italic">Note: {app.employer_note}</p>
                  )}
                </div>

                {app.status === 'pending' && (
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleReview(app.id, 'accepted')}
                      disabled={reviewing === app.id}
                      className="text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-500 transition disabled:opacity-50 font-medium">
                      {reviewing === app.id ? '...' : 'Accept'}
                    </button>
                    <button
                      onClick={() => handleReview(app.id, 'rejected', 'Not a fit at this time.')}
                      disabled={reviewing === app.id}
                      className="text-xs bg-red-50 text-red-600 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-100 transition disabled:opacity-50">
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Apply Panel (Freelancer) ─────────────────────────────────────────────────
function ApplyPanel({ project, user, onRefresh }: { project: Project; user: User; onRefresh: () => void }) {
  const [applying, setApplying] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ cover_letter: '', proposed_rate: '' })
  const [applied, setApplied] = useState(false)

  const isAssigned = project.freelancer_id === user.id
  const isTaken = !!project.freelancer_id && !isAssigned
  const isOpen = ['active', 'draft'].includes(project.status)

  const handleApply = async () => {
    setApplying(true)
    try {
      await projectsApi.apply(project.id, {
        cover_letter: form.cover_letter || undefined,
        proposed_rate: form.proposed_rate ? parseFloat(form.proposed_rate) : undefined,
      })
      toast.success('Application submitted!')
      setApplied(true)
      setShowForm(false)
      onRefresh()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Application failed')
    } finally {
      setApplying(false)
    }
  }

  const handleWithdraw = async () => {
    setWithdrawing(true)
    try {
      await projectsApi.withdrawApplication(project.id)
      toast.success('Application withdrawn')
      setApplied(false)
      onRefresh()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Withdrawal failed')
    } finally {
      setWithdrawing(false)
    }
  }

  if (isAssigned) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-2xl p-5 mb-6">
        <div className="flex items-center gap-2 text-green-700 font-semibold">
          <span>✓</span>
          <span>You are assigned to this project</span>
        </div>
        <p className="text-sm text-green-600 mt-1">Submit your work on each milestone below.</p>
      </div>
    )
  }

  if (isTaken) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 mb-6 text-sm text-slate-500">
        This project has been assigned to another freelancer.
      </div>
    )
  }

  if (!isOpen) return null

  if (applied) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-5 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold text-blue-800">Application submitted</div>
            <p className="text-sm text-blue-600 mt-0.5">Waiting for the employer to review your application.</p>
          </div>
          <button onClick={handleWithdraw} disabled={withdrawing}
            className="text-xs text-red-500 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-50 transition">
            {withdrawing ? '...' : 'Withdraw'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-6">
      <h2 className="font-semibold text-slate-900 mb-1">Apply for this Project</h2>
      <p className="text-sm text-slate-500 mb-4">Submit an application and the employer will review it.</p>

      {!showForm ? (
        <button onClick={() => setShowForm(true)}
          className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-500 transition text-sm">
          Apply Now
        </button>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Cover Letter <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <textarea rows={4} value={form.cover_letter}
              onChange={e => setForm({ ...form, cover_letter: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Introduce yourself and explain why you're a great fit..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Proposed Rate ($) <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input type="number" value={form.proposed_rate}
              onChange={e => setForm({ ...form, proposed_rate: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. 4500" />
          </div>
          <div className="flex gap-3">
            <button onClick={handleApply} disabled={applying}
              className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-500 transition disabled:opacity-50 text-sm">
              {applying ? 'Submitting...' : 'Submit Application'}
            </button>
            <button onClick={() => setShowForm(false)}
              className="px-5 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 transition">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ProjectPage() {
  const params = useParams()
  const router = useRouter()
  const [project, setProject] = useState<Project | null>(null)
  const [escrow, setEscrow] = useState<EscrowAccount | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [acceptedFreelancers, setAcceptedFreelancers] = useState<Application[]>([])

  const load = useCallback(async () => {
    const id = params.id as string
    const [projRes, escrowRes, appsRes] = await Promise.allSettled([
      projectsApi.get(id),
      paymentsApi.getEscrow(id),
      projectsApi.getApplications(id),
    ])
    if (projRes.status === 'fulfilled') setProject(projRes.value.data)
    if (escrowRes.status === 'fulfilled') setEscrow(escrowRes.value.data)
    if (appsRes.status === 'fulfilled') {
      setAcceptedFreelancers((appsRes.value.data as Application[]).filter(a => a.status === 'accepted'))
    }
    setLoading(false)
  }, [params.id])

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (!stored) { router.push('/auth/login'); return }
    setUser(JSON.parse(stored))
    load()
  }, [params.id, load, router])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!project || !user) return null

  const completedMilestones = project.milestones.filter(m => m.status === 'paid').length
  const progress = project.milestones.length > 0
    ? Math.round((completedMilestones / project.milestones.length) * 100) : 0

  const projectStatusColor: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-600',
    active: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-amber-100 text-amber-700',
    completed: 'bg-green-100 text-green-700',
    disputed: 'bg-red-100 text-red-700',
    cancelled: 'bg-slate-200 text-slate-500',
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-3 sticky top-0 z-10">
        <Link href="/dashboard" className="text-blue-600 text-sm hover:underline">← Dashboard</Link>
        <span className="text-slate-300">/</span>
        <span className="text-slate-700 font-medium text-sm truncate">{project.title}</span>
        <span className={`ml-auto text-xs px-2.5 py-1 rounded-full font-medium ${projectStatusColor[project.status]}`}>
          {project.status.replace(/_/g, ' ')}
        </span>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Project Header */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-slate-900">{project.title}</h1>
              <p className="text-slate-500 text-sm mt-1 leading-relaxed">{project.description}</p>
              <div className="flex flex-wrap gap-2 mt-3">
                <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full capitalize">
                  {project.project_type.replace(/_/g, ' ')}
                </span>
                {project.ai_roadmap?.complexity && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full capitalize">
                    {project.ai_roadmap.complexity} complexity
                  </span>
                )}
                {project.ai_roadmap?.employer_specs?.tech_stack?.map((t: string) => (
                  <span key={t} className="text-xs bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">{t}</span>
                ))}
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-2xl font-bold text-slate-900">${project.total_budget.toLocaleString()}</div>
              <div className="text-xs text-slate-400 mt-0.5">Total Budget</div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-5">
            <div className="flex justify-between text-xs text-slate-500 mb-1.5">
              <span>{completedMilestones} of {project.milestones.length} milestones completed</span>
              <span className="font-medium">{progress}%</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>

        {/* Freelancer: Apply panel */}
        {user.role === 'freelancer' && (
          <ApplyPanel project={project} user={user} onRefresh={load} />
        )}

        {/* Employer: Applications panel (only when project is active/open) */}
        {user.role === 'employer' && ['active', 'draft'].includes(project.status) && (
          <ApplicationsPanel projectId={project.id} onRefresh={load} />
        )}

        {/* Escrow Panel */}
        {escrow && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
            <h2 className="font-semibold text-slate-900 mb-4">Escrow Account</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              {[
                { label: 'Total Deposited', value: `$${escrow.total_deposited.toFixed(2)}`, color: 'text-slate-900' },
                { label: 'Locked', value: `$${escrow.locked_balance.toFixed(2)}`, color: 'text-amber-600' },
                { label: 'Released', value: `$${escrow.released_balance.toFixed(2)}`, color: 'text-green-600' },
                { label: 'Refunded', value: `$${escrow.refunded_balance.toFixed(2)}`, color: 'text-slate-400' },
              ].map(item => (
                <div key={item.label} className="bg-slate-50 rounded-xl p-3">
                  <div className={`text-xl font-bold ${item.color}`}>{item.value}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Discussion */}
        <DiscussionPanel projectId={project.id} user={user} />

        {/* Milestones */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-900">Milestones</h2>
          <span className="text-xs text-slate-400">{project.milestones.length} total</span>
        </div>
        <div className="space-y-4">
          {project.milestones
            .sort((a, b) => a.order_index - b.order_index)
            .map(m => (
              <MilestoneCard key={m.id} m={m} user={user} projectId={project.id}
                acceptedFreelancers={acceptedFreelancers} onRefresh={load} />
            ))}
        </div>
      </div>
    </div>
  )
}
