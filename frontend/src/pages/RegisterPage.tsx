import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function RegisterPage() {
  const navigate = useNavigate()
  const register = useAuthStore((s) => s.register)
  const [form, setForm] = useState({ handle: '', email: '', display_name: '', password: '', consent: false })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const set = (k: keyof typeof form, v: string | boolean) =>
    setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.consent) { setError('You must agree to the privacy policy to continue.'); return }
    setError(null)
    setLoading(true)
    try {
      await register({ ...form, consent: form.consent })
      navigate('/feed', { replace: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Join VERIDA</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Real humans, real moments.</p>
        </div>

        <form onSubmit={submit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="display_name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Name</label>
            <input
              id="display_name"
              type="text"
              required
              value={form.display_name}
              onChange={(e) => set('display_name', e.target.value)}
              className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Your name"
              maxLength={60}
            />
          </div>

          <div>
            <label htmlFor="handle" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Handle</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">@</span>
              <input
                id="handle"
                type="text"
                required
                value={form.handle}
                onChange={(e) => set('handle', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                className="w-full pl-8 pr-4 py-3 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="yourhandle"
                maxLength={30}
                pattern="[a-z0-9_]+"
              />
            </div>
          </div>

          <div>
            <label htmlFor="reg-email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Email</label>
            <input
              id="reg-email"
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="reg-password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Password</label>
            <input
              id="reg-password"
              type="password"
              required
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => set('password', e.target.value)}
              className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Min 12 characters"
              minLength={12}
            />
          </div>

          <div className="flex items-start gap-3">
            <input
              id="consent"
              type="checkbox"
              checked={form.consent}
              onChange={(e) => set('consent', e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="consent" className="text-sm text-slate-600 dark:text-slate-400">
              I agree to the{' '}
              <Link to="/privacy" className="text-indigo-600 dark:text-indigo-400 hover:underline">
                privacy policy
              </Link>{' '}
              and consent to data processing for this service.
            </label>
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-500 dark:text-red-400 text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white rounded-xl font-semibold transition mt-2"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </main>
  )
}
