import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

// Lazy-loaded pages for small bundle
const LoginPage    = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const FeedPage     = lazy(() => import('./pages/FeedPage'))
const CapturePage  = lazy(() => import('./pages/CapturePage'))
const CirclesPage  = lazy(() => import('./pages/CirclesPage'))
const ProfilePage  = lazy(() => import('./pages/ProfilePage'))
const ArchivePage  = lazy(() => import('./pages/ArchivePage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-slate-950">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" aria-label="Loading" />
    </div>
  )
}

function RequireAuth() {
  const { isAuthenticated, restoreSession } = useAuthStore()
  useEffect(() => { restoreSession() }, [restoreSession])
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Outlet />
}

function HomePage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (isAuthenticated) return <Navigate to="/feed" replace />
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-white px-6 text-center">
      <h1 className="text-5xl font-bold mb-4 tracking-tight">VERIDA</h1>
      <p className="text-slate-400 text-lg mb-10 max-w-xs">
        Proof-of-Human Social Web — share spontaneous daily moments.
      </p>
      <div className="flex gap-4 flex-wrap justify-center">
        <a href="/login" className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold text-sm transition">
          Sign in
        </a>
        <a href="/register" className="px-8 py-3.5 border border-slate-600 hover:border-slate-400 rounded-xl font-semibold text-sm transition">
          Sign up
        </a>
      </div>
    </main>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Suspense fallback={<Spinner />}>
          <Routes>
            {/* Public */}
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected — inside Layout */}
            <Route element={<RequireAuth />}>
              <Route element={<Layout />}>
                <Route path="/feed" element={<FeedPage />} />
                <Route path="/capture" element={<CapturePage />} />
                <Route path="/circles" element={<CirclesPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/archive" element={<ArchivePage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Route>

            {/* Catch-all */}
            <Route
              path="*"
              element={
                <main className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-white gap-4">
                  <h2 className="text-4xl font-bold">404</h2>
                  <p className="text-slate-400">Page not found.</p>
                  <a href="/" className="text-indigo-400 hover:underline text-sm">← Go home</a>
                </main>
              }
            />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
