import { BrowserRouter, Route, Routes, Link } from 'react-router-dom'

// ── Page placeholders (M2 will fill these in) ─────────────────────────────────
function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-900 text-white">
      <div className="max-w-lg text-center px-4">
        <h1 className="text-4xl font-bold mb-4">VERIDA</h1>
        <p className="text-slate-400 mb-8">
          Proof-of-Human Social Web — share spontaneous daily moments.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/login"
            className="bg-indigo-600 hover:bg-indigo-500 px-6 py-2 rounded-lg font-medium transition"
          >
            Log in
          </Link>
          <Link
            to="/register"
            className="border border-slate-600 hover:border-slate-400 px-6 py-2 rounded-lg font-medium transition"
          >
            Sign up
          </Link>
        </div>
      </div>
    </main>
  )
}

function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 text-white">
      <div className="w-full max-w-sm px-4">
        <h2 className="text-2xl font-bold mb-6">Log in</h2>
        <p className="text-slate-400 text-sm">Login form — implemented in M2.</p>
        <Link to="/" className="text-indigo-400 text-sm mt-4 inline-block">← Back</Link>
      </div>
    </main>
  )
}

function RegisterPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 text-white">
      <div className="w-full max-w-sm px-4">
        <h2 className="text-2xl font-bold mb-6">Create account</h2>
        <p className="text-slate-400 text-sm">Registration form — implemented in M2.</p>
        <Link to="/" className="text-indigo-400 text-sm mt-4 inline-block">← Back</Link>
      </div>
    </main>
  )
}

function FeedPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 text-white">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Your Feed</h2>
        <p className="text-slate-400">Daily moments — implemented in M2.</p>
      </div>
    </main>
  )
}

function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 text-white">
      <div className="text-center">
        <h2 className="text-4xl font-bold mb-4">404</h2>
        <p className="text-slate-400 mb-4">Page not found.</p>
        <Link to="/" className="text-indigo-400">← Go home</Link>
      </div>
    </main>
  )
}

// ── App shell ─────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/feed" element={<FeedPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
