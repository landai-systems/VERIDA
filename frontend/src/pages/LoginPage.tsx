import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login({ email, password })
      navigate('/feed', { replace: true })
    } catch {
      setError('Invalid email or password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-12 bg-[#080810]">
      {/* Logo */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-black text-white tracking-tight">VERIDA</h1>
        <p className="mt-2 text-sm text-slate-500">Real humans, real moments.</p>
      </div>

      {/* Card */}
      <div className="w-full max-w-sm backdrop-blur-xl bg-white/5 border border-white/10 rounded-3xl p-8 shadow-[0_0_40px_rgba(99,102,241,0.1)]">
        <h2 className="text-lg font-semibold text-white mb-6">Sign in</h2>

        <form onSubmit={submit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full transition-colors"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div role="alert" className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-full px-4 py-2 text-sm">
              <span className="text-base">⚠</span>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 disabled:opacity-60 text-white font-semibold py-3 rounded-xl w-full transition-all duration-200 flex items-center justify-center gap-2 mt-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Signing in…
              </>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          No account?{' '}
          <Link to="/register" className="text-indigo-400 font-medium hover:text-indigo-300 transition-colors">
            Sign up free
          </Link>
        </p>
      </div>
    </main>
  )
}
