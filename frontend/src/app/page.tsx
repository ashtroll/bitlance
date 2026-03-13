import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-950 via-slate-900 to-slate-800 text-white">
      <nav className="border-b border-white/10 px-6 py-4 flex justify-between items-center">
        <span className="text-xl font-bold tracking-tight">⚡ Bitlance</span>
        <div className="flex gap-3">
          <Link href="/auth/login" className="px-4 py-2 rounded-lg border border-white/20 text-sm hover:bg-white/10 transition">
            Sign In
          </Link>
          <Link href="/auth/register" className="px-4 py-2 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 transition">
            Get Started
          </Link>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-500/20 border border-blue-400/30 rounded-full px-4 py-1.5 text-sm text-blue-300 mb-8">
          <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></span>
          AI-Powered Project Verification
        </div>

        <h1 className="text-5xl md:text-6xl font-extrabold mb-6 leading-tight">
          Hire & Build with<br />
          <span className="text-blue-400">Zero Trust Friction</span>
        </h1>

        <p className="text-lg text-slate-300 max-w-2xl mx-auto mb-12">
          Bitlance automatically decomposes projects into milestones, holds payments in escrow,
          and releases funds only when AI verifies completion.
        </p>

        <div className="flex flex-wrap justify-center gap-4 mb-20">
          <Link href="/auth/register?role=employer"
            className="px-8 py-4 bg-blue-600 rounded-xl font-semibold hover:bg-blue-500 transition text-lg">
            Post a Project →
          </Link>
          <Link href="/auth/register?role=freelancer"
            className="px-8 py-4 bg-white/10 border border-white/20 rounded-xl font-semibold hover:bg-white/20 transition text-lg">
            Find Work →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          {[
            { icon: "🤖", title: "AI Milestone Generation", desc: "Describe your project in plain English. AI breaks it into verifiable milestones automatically." },
            { icon: "🔒", title: "Escrow Protection", desc: "Funds are locked per milestone and only released after AI verification — no manual disputes needed." },
            { icon: "📊", title: "PFI Reputation Score", desc: "Every freelancer earns a Professional Fidelity Index score (300–850) updated after each milestone." },
          ].map((f) => (
            <div key={f.title} className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
