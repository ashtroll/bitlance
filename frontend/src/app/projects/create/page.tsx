'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { projectsApi, paymentsApi } from '@/lib/api'

const PROJECT_TYPES = [
  'web_application', 'mobile_app', 'api', 'content', 'design', 'data_science', 'other'
]

export default function CreateProjectPage() {
  const router = useRouter()
  const [step, setStep] = useState<'form' | 'generating' | 'review'>('form')
  const [form, setForm] = useState({
    title: '', description: '', total_budget: '', project_type: '',
    tech_stack: '', language_preferences: '', system_requirements: '', special_notes: '',
  })
  const [project, setProject] = useState<any>(null)
  const [depositAmount, setDepositAmount] = useState('')

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setStep('generating')
    try {
      const tech_stack = form.tech_stack
        ? form.tech_stack.split(',').map(s => s.trim()).filter(Boolean)
        : []
      const { data } = await projectsApi.create({
        title: form.title,
        description: form.description,
        total_budget: parseFloat(form.total_budget),
        project_type: form.project_type || undefined,
        tech_stack,
        language_preferences: form.language_preferences,
        system_requirements: form.system_requirements,
        special_notes: form.special_notes,
      })
      setProject(data)
      setDepositAmount(form.total_budget)
      setStep('review')
      toast.success('Project created with AI milestones!')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create project')
      setStep('form')
    }
  }

  const handleDeposit = async () => {
    if (!project) return
    try {
      await paymentsApi.deposit({ project_id: project.id, amount: parseFloat(depositAmount) })
      toast.success('Funds deposited to escrow!')
      router.push(`/projects/${project.id}`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Deposit failed')
    }
  }

  if (step === 'generating') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-slate-800">AI is analyzing your project...</h2>
          <p className="text-slate-500 mt-2 text-sm">Generating milestones and roadmap</p>
        </div>
      </div>
    )
  }

  if (step === 'review' && project) {
    return (
      <div className="min-h-screen bg-slate-50">
        <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
          <Link href="/dashboard" className="text-blue-600 text-sm">← Dashboard</Link>
          <span className="text-slate-800 font-semibold">Review AI Roadmap</span>
        </nav>
        <div className="max-w-3xl mx-auto px-6 py-8">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
            <h2 className="text-xl font-bold text-slate-900 mb-1">{project.title}</h2>
            <p className="text-slate-500 text-sm mb-4">{project.description}</p>
            <div className="flex gap-3 text-sm">
              <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full capitalize">
                {project.project_type.replace('_', ' ')}
              </span>
              <span className="bg-green-50 text-green-700 px-3 py-1 rounded-full">
                ${project.total_budget.toLocaleString()} budget
              </span>
            </div>
          </div>

          <h3 className="font-semibold text-slate-800 mb-3">AI-Generated Milestones</h3>
          <div className="space-y-3 mb-8">
            {project.milestones.map((m: any, i: number) => (
              <div key={m.id} className="bg-white rounded-xl border border-slate-200 p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                      {i + 1}
                    </span>
                    <div>
                      <div className="font-semibold text-slate-900">{m.title}</div>
                      <div className="text-sm text-slate-500 mt-0.5">{m.description}</div>
                    </div>
                  </div>
                  <div className="text-right ml-4 flex-shrink-0">
                    <div className="font-semibold text-slate-900">${m.payment_amount.toFixed(2)}</div>
                    <div className="text-xs text-slate-400">{m.deadline_days} days</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-800 mb-4">Fund Escrow</h3>
            <div className="flex gap-3">
              <input
                type="number" value={depositAmount}
                onChange={e => setDepositAmount(e.target.value)}
                className="flex-1 border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Deposit amount"
              />
              <button onClick={handleDeposit}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-500 transition text-sm">
                Deposit & Activate
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Funds will be held in escrow and released milestone-by-milestone upon AI verification.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <Link href="/dashboard" className="text-blue-600 text-sm">← Dashboard</Link>
        <span className="text-slate-800 font-semibold">New Project</span>
      </nav>
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl border border-slate-200 p-8">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Describe your project</h1>
          <p className="text-slate-500 text-sm mb-6">
            AI will automatically break it into milestones and create an escrow-backed roadmap.
          </p>
          <form onSubmit={handleCreate} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Project Title</label>
              <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. SaaS Landing Page with Auth" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Project Description</label>
              <textarea required rows={4} value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                placeholder="Describe what you need built in detail..." />
            </div>

            {/* Specification fields */}
            <div className="border border-blue-100 rounded-xl p-4 bg-blue-50/40 space-y-4">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Technical Specifications (AI will strictly follow these)</p>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Tech Stack <span className="text-slate-400 font-normal">(comma-separated)</span>
                </label>
                <input value={form.tech_stack} onChange={e => setForm({ ...form, tech_stack: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  placeholder="e.g. React, Node.js, PostgreSQL, Docker" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Language / Framework Preferences</label>
                <input value={form.language_preferences} onChange={e => setForm({ ...form, language_preferences: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  placeholder="e.g. Python preferred, no PHP, TypeScript only" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">System / Infrastructure Requirements</label>
                <input value={form.system_requirements} onChange={e => setForm({ ...form, system_requirements: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  placeholder="e.g. Must run on AWS Lambda, mobile-first, supports 10k concurrent users" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Special Notes / Constraints</label>
                <textarea rows={2} value={form.special_notes} onChange={e => setForm({ ...form, special_notes: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none bg-white"
                  placeholder="e.g. Must comply with GDPR, no third-party auth libraries, include unit tests" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Total Budget ($)</label>
                <input required type="number" min="1" value={form.total_budget}
                  onChange={e => setForm({ ...form, total_budget: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="5000" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Project Type (optional)</label>
                <select value={form.project_type} onChange={e => setForm({ ...form, project_type: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">AI will detect</option>
                  {PROJECT_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                </select>
              </div>
            </div>
            <button type="submit"
              className="w-full bg-blue-600 text-white rounded-lg py-3 font-medium hover:bg-blue-500 transition">
              Generate AI Roadmap →
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
