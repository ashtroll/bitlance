'use client'
import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'

export default function RegisterPage() {
  const router = useRouter()
  const params = useSearchParams()
  const defaultRole = params.get('role') || 'freelancer'

  const [form, setForm] = useState({
    email: '', username: '', password: '',
    full_name: '', role: defaultRole,
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.register(form)
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      toast.success('Account created!')
      router.push('/dashboard')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold text-blue-600">⚡ Bitlance</Link>
          <h1 className="text-2xl font-semibold mt-4 text-slate-800">Create your account</h1>
        </div>
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 space-y-5">
          {/* Role Toggle */}
          <div className="flex rounded-lg border border-slate-200 overflow-hidden">
            {['employer', 'freelancer'].map((r) => (
              <button key={r} type="button"
                onClick={() => setForm({ ...form, role: r })}
                className={`flex-1 py-2.5 text-sm font-medium capitalize transition ${form.role === r ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-50'}`}>
                {r === 'employer' ? '🏢 Employer' : '💼 Freelancer'}
              </button>
            ))}
          </div>

          {[
            { label: 'Full Name', key: 'full_name', type: 'text', placeholder: 'John Doe' },
            { label: 'Username', key: 'username', type: 'text', placeholder: 'johndoe' },
            { label: 'Email', key: 'email', type: 'email', placeholder: 'you@example.com' },
            { label: 'Password', key: 'password', type: 'password', placeholder: '••••••••' },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
              <input
                type={type} required value={(form as any)[key]}
                onChange={e => setForm({ ...form, [key]: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={placeholder}
              />
            </div>
          ))}

          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-medium hover:bg-blue-500 transition disabled:opacity-50">
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
          <p className="text-center text-sm text-slate-500">
            Have an account?{' '}
            <Link href="/auth/login" className="text-blue-600 font-medium hover:underline">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
