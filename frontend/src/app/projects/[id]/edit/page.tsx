'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { projectsApi } from '@/lib/api'
import type { Project } from '@/lib/types'

export default function EditProjectPage() {
  const router = useRouter()
  const { id } = useParams<{ id: string }>()

  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', total_budget: '' })

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (!stored) { router.push('/auth/login'); return }
    const user = JSON.parse(stored)
    if (user.role !== 'employer') { router.push('/dashboard'); return }

    projectsApi.get(id).then(r => {
      const p: Project = r.data
      setProject(p)
      setForm({
        title: p.title,
        description: p.description,
        total_budget: String(p.total_budget),
      })
    }).catch(() => {
      toast.error('Project not found')
      router.push('/dashboard')
    }).finally(() => setLoading(false))
  }, [id, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const budget = parseFloat(form.total_budget)
    if (!form.title.trim() || !form.description.trim()) {
      toast.error('Title and description are required')
      return
    }
    if (isNaN(budget) || budget <= 0) {
      toast.error('Enter a valid budget')
      return
    }
    setSaving(true)
    try {
      await projectsApi.update(id, {
        title: form.title.trim(),
        description: form.description.trim(),
        total_budget: budget,
      })
      toast.success('Project updated')
      router.push(`/projects/${id}`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!project) return null

  const isEditable = ['draft', 'active'].includes(project.status)

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-lg font-bold text-blue-600">⚡ Bitlance</Link>
        <Link href={`/projects/${id}`} className="text-sm text-slate-500 hover:text-slate-800">
          ← Back to project
        </Link>
      </nav>

      <div className="max-w-2xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Edit Project</h1>
        <p className="text-sm text-slate-500 mb-8">
          Changes apply to the project details. AI-generated milestones are not affected.
        </p>

        {!isEditable && (
          <div className="mb-6 p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
            This project is <span className="font-semibold capitalize">{project.status.replace('_', ' ')}</span> and cannot be edited.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Title</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              disabled={!isEditable || saving}
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
            <textarea
              rows={6}
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              disabled={!isEditable || saving}
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Total Budget (USD)</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
              <input
                type="number"
                min="1"
                step="0.01"
                value={form.total_budget}
                onChange={e => setForm(f => ({ ...f, total_budget: e.target.value }))}
                disabled={!isEditable || saving}
                className="w-full pl-8 pr-4 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={!isEditable || saving}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
            <Link
              href={`/projects/${id}`}
              className="px-6 py-2.5 rounded-lg border border-slate-300 text-slate-700 font-medium hover:bg-slate-50 transition text-sm flex items-center"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
