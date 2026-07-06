import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function RegisterPage() {
  const navigate = useNavigate()
  const register = useAuthStore((s) => s.register)
  const [form, setForm] = useState({
    handle: '',
    email: '',
    display_name: '',
    password: '',
    consent: false,
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const set = (k: keyof typeof form, v: string | boolean) =>
    setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.consent) {
      setError('You must agree to the privacy policy to continue.')
      return
    }
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
    <main className="min-h-screen flex items-center justify-center px-4 py-12 bg-[#080810]">
      <div className="w-full max-w-4xl flex gap-12 items-center">
        {/* Left: tagline (desktop only) */}
        <div className="hidden md:flex flex-col flex-1 gap-8">
          <div>
            <h1 className="text-5xl font-black text-white tracking-tight leading-tight">VERIDA</h1>
            <p className="mt-3 text-xl text-slate-400 font-light">Real humans, real moments.</p>
          </div>
          <ul className="space-y-4">
            {[
              { icon: '📸', title: 'Daily spontaneous moments', desc: 'One capture per day, no editing.' },
              { icon: '✅', title: 'Human-verified authenticity', desc: 'AI checks every post is real.' },
              { icon: '🔒', title: 'Private circles', desc: 'Share only with people you choose.' },
              { icon: '🌍', title: 'GDPR-first design', desc: 'Your data, your rights, always.' },
            ].map(({ icon, title, desc }) => (
              <li key={title} className="flex items-start gap-3">
                <span className="text-2xl leading-none mt-0.5">{icon}</span>
                <div>
                  <p className="text-white font-medium text-sm">{title}</p>
                  <p className="text-slate-500 text-xs mt-0.5">{desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Right: form */}
        <div className="flex-1 w-full max-w-sm mx-auto md:mx-0">
          {/* Mobile logo */}
          <div className="md:hidden text-center mb-8">
            <h1 className="text-4xl font-black text-white tracking-tight">VERIDA</h1>
            <p className="mt-2 text-sm text-slate-500">Real humans, real moments.</p>
          </div>

          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-3xl p-8 shadow-[0_0_40px_rgba(99,102,241,0.1)]">
            <h2 className="text-lg font-semibold text-white mb-6">Create account</h2>

            <form onSubmit={submit} className="space-y-4" noValidate>
              <div>
                <label htmlFor="display_name" className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                  Name
                </label>
                <input
                  id="display_name"
                  type="text"
                  required
                  value={form.display_name}
                  onChange={(e) => set('display_name', e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full transition-colors"
                  placeholder="Your name"
                  maxLength={60}
                />
              </div>

              <div>
                <label htmlFor="handle" className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                  Handle
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none select-none">@</span>
                  <input
                    id="handle"
                    type="text"
                    required
                    value={form.handle}
                    onChange={(e) => set('handle', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                    className="bg-white/5 border border-white/10 rounded-xl pl-8 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full transition-colors"
                    placeholder="yourhandle"
                    maxLength={30}
                    pattern="[a-z0-9_]+"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="reg-email" className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                  Email
                </label>
                <input
                  id="reg-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full transition-colors"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label htmlFor="reg-password" className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                  Password
                </label>
                <input
                  id="reg-password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(e) => set('password', e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full transition-colors"
                  placeholder="Min 12 characters"
                  minLength={12}
                />
              </div>

              {/* Consent checkbox */}
              <label className="flex items-start gap-3 cursor-pointer group">
                <div className="relative mt-0.5 flex-shrink-0">
                  <input
                    id="consent"
                    type="checkbox"
                    checked={form.consent}
                    onChange={(e) => set('consent', e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    className={`w-5 h-5 rounded-md border transition-all duration-150 flex items-center justify-center ${
                      form.consent
                        ? 'bg-indigo-500 border-indigo-500'
                        : 'bg-white/5 border-white/20 group-hover:border-white/40'
                    }`}
                    onClick={() => set('consent', !form.consent)}
                    aria-hidden="true"
                  >
                    {form.consent && (
                      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </div>
                <span className="text-sm text-slate-400 leading-relaxed">
                  I agree to the{' '}
                  <Link to="/privacy" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">
                    privacy policy
                  </Link>{' '}
                  and consent to data processing.
                </span>
              </label>

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
                    Creating account…
                  </>
                ) : (
                  'Create account'
                )}
              </button>
            </form>

            <p className="text-center text-sm text-slate-500 mt-6">
              Already have an account?{' '}
              <Link to="/login" className="text-indigo-400 font-medium hover:text-indigo-300 transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
