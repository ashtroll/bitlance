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

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (!stored) { router.push('/auth/login'); return }
    const u: User = JSON.parse(stored)
    setUser(u)

    Promise.all([
      projectsApi.list().then(r => setProjects(r.data)),
      u.role === 'freelancer'
        ? reputationApi.me().then(r => setReputation(r.data)).catch(() => null)
        : Promise.resolve(),
    ]).finally(() => setLoading(false))
  }, [router])

  const handleLogout = () => {
    localStorage.clear()
    router.push('/')
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

        {/* Stats Row for Freelancers */}
        {user?.role === 'freelancer' && reputation && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'PFI Score', value: Math.round(reputation.pfi_score) },
              { label: 'Success Rate', value: `${Math.round(reputation.milestone_success_rate * 100)}%` },
              { label: 'Quality Score', value: `${Math.round(reputation.avg_quality_score * 100)}%` },
              { label: 'Total Milestones', value: reputation.total_milestones },
            ].map(stat => (
              <div key={stat.label} className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="text-2xl font-bold text-slate-900">{stat.value}</div>
                <div className="text-xs text-slate-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

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
              <Link key={p.id} href={`/projects/${p.id}`}
                className="block bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition">
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
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
