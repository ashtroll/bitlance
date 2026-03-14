'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { projectsApi, reputationApi } from '@/lib/api'
import type { Project, ReputationScore, User } from '@/lib/types'

function PFIBadge({ score }: { score: number }) {
  const color = score >= 700 ? 'text-green-600 bg-green-50 border-green-200'
    : score >= 500 ? 'text-yellow-600 bg-yellow-50 border-yellow-200'
    : 'text-red-600 bg-red-50 border-red-200'
  const label = score >= 700 ? 'Excellent' : score >= 500 ? 'Good' : 'Developing'
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full border ${color}`}>
      ★ {Math.round(score)} PFI · {label}
    </span>
  )
}

const statusColor: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-600',
  active: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-700',
  cancelled: 'bg-slate-200 text-slate-500',
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [reputation, setReputation] = useState<ReputationScore | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState<string | null>(null)

  const loadProjects = () => projectsApi.list().then(r => setProjects(r.data))

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (!stored) { router.push('/auth/login'); return }
    const u: User = JSON.parse(stored)
    setUser(u)

    Promise.all([
      loadProjects(),
      u.role === 'freelancer'
        ? reputationApi.me().then(r => setReputation(r.data)).catch(() => null)
        : Promise.resolve(),
    ]).finally(() => setLoading(false))
  }, [router])

  const handleLogout = () => {
    localStorage.clear()
    router.push('/')
  }

  const handleCancel = async (e: React.MouseEvent, projectId: string) => {
    e.preventDefault()
    if (!confirm('Cancel this project? This cannot be undone.')) return
    setActionId(projectId)
    try {
      await projectsApi.cancel(projectId)
      toast.success('Project cancelled')
      await loadProjects()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Cancel failed')
    } finally {
      setActionId(null)
    }
  }

  const handleDelete = async (e: React.MouseEvent, projectId: string) => {
    e.preventDefault()
    if (!confirm('Permanently delete this project? This cannot be undone.')) return
    setActionId(projectId)
    try {
      await projectsApi.delete(projectId)
      toast.success('Project deleted')
      setProjects(prev => prev.filter(p => p.id !== projectId))
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Delete failed')
    } finally {
      setActionId(null)
    }
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-lg font-bold text-blue-600">⚡ Bitlance</Link>
        <div className="flex items-center gap-4">
          {user?.role === 'freelancer' && reputation && <PFIBadge score={reputation.pfi_score} />}
          <span className="text-sm text-slate-600 capitalize">{user?.role} · {user?.username}</span>
          <button onClick={handleLogout} className="text-sm text-slate-500 hover:text-slate-800">Sign out</button>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-slate-900">
            {user?.role === 'employer' ? 'Your Projects' : 'Your Work'}
          </h1>
          {user?.role === 'employer' && (
            <Link href="/projects/create"
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-500 transition text-sm">
              + New Project
            </Link>
          )}
        </div>

        {/* PFI Dashboard for Freelancers */}
        {user?.role === 'freelancer' && reputation && (() => {
          const score = reputation.pfi_score
          const tier = score >= 750 ? { name: 'Platinum', icon: '💎', color: 'purple' }
            : score >= 650 ? { name: 'Gold', icon: '🥇', color: 'yellow' }
            : score >= 500 ? { name: 'Silver', icon: '🥈', color: 'blue' }
            : { name: 'Bronze', icon: '🥉', color: 'amber' }
          const pct = Math.round(((score - 300) / 550) * 100)
          const metrics = [
            { label: 'Success Rate', value: reputation.milestone_success_rate, weight: '40%', color: 'green' },
            { label: 'Quality Score', value: reputation.avg_quality_score, weight: '30%', color: 'blue' },
            { label: 'On-Time Rate', value: reputation.deadline_adherence_rate, weight: '20%', color: 'amber' },
            { label: 'Dispute-Free', value: 1 - reputation.dispute_rate, weight: '10%', color: 'red' },
          ]
          return (
            <div className="mb-8 bg-white rounded-2xl border border-slate-200 p-6">
              <div className="flex items-start justify-between gap-6 mb-5">
                <div>
                  <div className="text-5xl font-black text-slate-900 leading-none">{Math.round(score)}</div>
                  <div className="text-sm text-slate-400 mt-1">Professional Fidelity Index · out of 850</div>
                  <div className="mt-2.5">
                    <span className={`inline-flex items-center gap-1.5 text-sm font-bold px-3 py-1 rounded-full border
                      ${tier.color === 'purple' ? 'bg-purple-50 text-purple-800 border-purple-200' :
                        tier.color === 'yellow' ? 'bg-yellow-50 text-yellow-800 border-yellow-200' :
                        tier.color === 'blue' ? 'bg-blue-50 text-blue-800 border-blue-200' :
                        'bg-amber-50 text-amber-800 border-amber-200'}`}>
                      {tier.icon} {tier.name}
                    </span>
                  </div>
                </div>
                <div className="flex-1 max-w-sm">
                  <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                    <span>300</span><span className="font-semibold text-slate-700">{Math.round(score)} / 850</span><span>850</span>
                  </div>
                  <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-700
                      ${tier.color === 'purple' ? 'bg-purple-500' :
                        tier.color === 'yellow' ? 'bg-yellow-500' :
                        tier.color === 'blue' ? 'bg-blue-500' : 'bg-amber-500'}`}
                      style={{ width: `${pct}%` }} />
                  </div>
                  <div className="text-xs text-slate-400 mt-1 text-center">{pct}% to maximum</div>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {metrics.map(m => (
                  <div key={m.label} className={`rounded-xl border p-3
                    ${m.color === 'green' ? 'bg-green-50 border-green-200 text-green-800' :
                      m.color === 'blue' ? 'bg-blue-50 border-blue-200 text-blue-800' :
                      m.color === 'amber' ? 'bg-amber-50 border-amber-200 text-amber-800' :
                      'bg-red-50 border-red-200 text-red-800'}`}>
                    <div className="text-xl font-bold">{Math.round(m.value * 100)}%</div>
                    <div className="text-xs font-medium mt-0.5">{m.label}</div>
                    <div className="text-xs opacity-60">weight {m.weight}</div>
                    <div className="mt-2 h-1.5 bg-white/50 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full
                        ${m.color === 'green' ? 'bg-green-500' :
                          m.color === 'blue' ? 'bg-blue-500' :
                          m.color === 'amber' ? 'bg-amber-500' : 'bg-red-400'}`}
                        style={{ width: `${m.value * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 text-center text-xs text-slate-400">
                PFI = 300 + 550 × (40% success + 30% quality + 20% on-time + 10% dispute-free)
                · {reputation.total_milestones} milestone{reputation.total_milestones !== 1 ? 's' : ''} completed
              </div>
            </div>
          )
        })()}

        {/* Projects List */}
        {projects.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <div className="text-4xl mb-3">📋</div>
            <p className="font-medium">No projects yet</p>
            {user?.role === 'employer' && (
              <Link href="/projects/create" className="mt-4 inline-block text-blue-600 text-sm hover:underline">
                Create your first project →
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((p) => (
              <div key={p.id} className="bg-white rounded-xl border border-slate-200 hover:shadow-md transition">
                <Link href={`/projects/${p.id}`} className="block p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-900">{p.title}</h3>
                      <p className="text-sm text-slate-500 mt-1 line-clamp-2">{p.description}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2 ml-4">
                      <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${statusColor[p.status]}`}>
                        {p.status.replace('_', ' ')}
                      </span>
                      <span className="text-sm font-semibold text-slate-700">${p.total_budget.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center gap-4 text-xs text-slate-400">
                    <span>{p.milestones.length} milestones</span>
                    <span>{p.milestones.filter(m => m.status === 'paid').length} completed</span>
                    <span className="capitalize">{p.project_type.replace('_', ' ')}</span>
                  </div>
                </Link>

                {/* Employer action buttons */}
                {user?.role === 'employer' && (
                  <div className="px-6 pb-4 flex gap-2 border-t border-slate-100 pt-3">
                    {['active', 'draft'].includes(p.status) && (
                      <Link
                        href={`/projects/${p.id}/edit`}
                        onClick={e => e.stopPropagation()}
                        className="text-xs px-3 py-1.5 rounded-lg border border-blue-200 text-blue-700 hover:bg-blue-50 transition">
                        Edit
                      </Link>
                    )}
                    {['active', 'draft'].includes(p.status) && (
                      <button
                        onClick={(e) => handleCancel(e, p.id)}
                        disabled={actionId === p.id}
                        className="text-xs px-3 py-1.5 rounded-lg border border-amber-200 text-amber-700 hover:bg-amber-50 transition disabled:opacity-50">
                        {actionId === p.id ? '...' : 'Cancel'}
                      </button>
                    )}
                    {['draft', 'active', 'cancelled'].includes(p.status) && (
                      <button
                        onClick={(e) => handleDelete(e, p.id)}
                        disabled={actionId === p.id}
                        className="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition disabled:opacity-50">
                        {actionId === p.id ? '...' : 'Delete'}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
