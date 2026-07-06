import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { consent as consentApi, ConsentRecord } from '../api/consent'
import { gdpr as gdprApi } from '../api/gdpr'
import { useAuthStore } from '../store/authStore'

interface SectionProps {
  title: string
  children: React.ReactNode
}

function SettingsSection({ title, children }: SectionProps) {
  return (
    <section>
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1 mb-2">{title}</h2>
      <div className="bg-white/5 border border-white/[0.08] rounded-2xl overflow-hidden divide-y divide-white/[0.06]">
        {children}
      </div>
    </section>
  )
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [records, setRecords] = useState<ConsentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteInput, setDeleteInput] = useState('')

  useEffect(() => {
    consentApi
      .getConsent()
      .then(setRecords)
      .catch(() => setRecords([]))
      .finally(() => setLoading(false))
  }, [])

  const withdraw = async (type: string) => {
    if (!confirm(`Withdraw consent for "${type}"? Some features may stop working.`)) return
    try {
      await consentApi.withdrawConsent(type)
      setRecords((prev) =>
        prev.map((r) =>
          r.consent_type === type ? { ...r, withdrawn_at: new Date().toISOString() } : r,
        ),
      )
      setMessage('Consent withdrawn.')
    } catch {
      setError('Failed to withdraw consent.')
    }
  }

  const exportData = async () => {
    setExporting(true)
    setError(null)
    try {
      const blob = await gdprApi.exportData()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `verida-export-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
      setMessage('Export downloaded.')
    } catch {
      setError('Export failed. Try again.')
    } finally {
      setExporting(false)
    }
  }

  const deleteAccount = async () => {
    if (deleteInput !== 'DELETE MY ACCOUNT') return
    setDeleting(true)
    try {
      await gdprApi.deleteAccount()
      await logout()
      navigate('/login', { replace: true })
    } catch {
      setError('Deletion failed. Contact support.')
      setDeleting(false)
    }
  }

  return (
    <div className="px-4 py-6 space-y-6 pb-32">
      <h1 className="text-2xl font-bold text-white pt-2">Settings</h1>

      {error && (
        <div role="alert" className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl px-4 py-3 text-sm">
          {error}
        </div>
      )}
      {message && (
        <div role="status" className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-2xl px-4 py-3 text-sm">
          {message}
        </div>
      )}

      {/* Account section */}
      {user && (
        <SettingsSection title="Account">
          <div className="px-4 py-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500/40 to-violet-600/40 border border-white/10 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
              {user.display_name.slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white text-sm truncate">{user.display_name}</p>
              <p className="text-xs text-slate-500">@{user.handle} · {user.email}</p>
            </div>
          </div>
          {!user.is_verified && (
            <div className="px-4 py-3 flex items-center gap-2 text-xs text-amber-400">
              <span>⚠</span>
              Email not verified — check your inbox.
            </div>
          )}
        </SettingsSection>
      )}

      {/* Consent management */}
      <SettingsSection title="Privacy & Data">
        <div className="px-4 py-4 space-y-3">
          <p className="text-xs text-slate-500 leading-relaxed">
            You can withdraw consent at any time. Withdrawal doesn't delete your data — use GDPR Erasure below for that.
          </p>
          {loading ? (
            <div className="flex justify-center py-3">
              <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : records.length === 0 ? (
            <p className="text-sm text-slate-500">No consent records on file.</p>
          ) : (
            <div className="space-y-3">
              {records.map((r) => (
                <div key={r.id} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white text-sm capitalize">
                      {r.consent_type.replace(/_/g, ' ')}
                    </p>
                    <p className="text-xs text-slate-500">
                      {r.withdrawn_at ? '🚫 Withdrawn' : '✓ Active'} · v{r.version}
                    </p>
                  </div>
                  {!r.withdrawn_at && (
                    <button
                      onClick={() => withdraw(r.consent_type)}
                      className="text-xs text-red-400/70 hover:text-red-400 transition-colors"
                    >
                      Withdraw
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* GDPR Export */}
        <div className="px-4 py-3">
          <button
            onClick={exportData}
            disabled={exporting}
            className="w-full py-3 bg-white/5 hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/[0.15] text-slate-200 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-60 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {exporting ? 'Preparing export…' : 'Export My Data (Article 20)'}
          </button>
        </div>
      </SettingsSection>

      {/* Danger Zone */}
      <SettingsSection title="Danger Zone">
        <div className="px-4 py-4 space-y-3">
          <p className="text-xs text-slate-500 leading-relaxed">
            Account deletion is permanent and irreversible. All your data will be erased within 30 days.
          </p>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="w-full py-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/40 text-red-400 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete Account & All Data (Article 17)
          </button>
        </div>
      </SettingsSection>

      {/* Sign out */}
      <button
        onClick={async () => {
          await logout()
          navigate('/login', { replace: true })
        }}
        className="w-full py-3 text-slate-500 text-sm hover:text-slate-300 transition-colors"
      >
        Sign out
      </button>

      {/* Delete confirm modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Confirm account deletion">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-md"
            onClick={() => setShowDeleteConfirm(false)}
          />
          <div className="relative backdrop-blur-xl bg-[#0d0d1a] border border-red-500/20 rounded-3xl p-6 max-w-sm w-full space-y-4">
            <div className="text-4xl text-center select-none">⚠️</div>
            <h2 className="text-lg font-bold text-white text-center">Delete your account?</h2>
            <p className="text-sm text-slate-400 text-center leading-relaxed">
              This is permanent. All your moments, circles, and data will be erased within 30 days.
            </p>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">
                Type DELETE MY ACCOUNT to confirm
              </label>
              <input
                type="text"
                value={deleteInput}
                onChange={(e) => setDeleteInput(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 w-full text-sm transition-colors"
                placeholder="DELETE MY ACCOUNT"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowDeleteConfirm(false); setDeleteInput('') }}
                className="flex-1 py-3 bg-white/5 hover:bg-white/10 text-slate-300 rounded-xl text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={deleteAccount}
                disabled={deleteInput !== 'DELETE MY ACCOUNT' || deleting}
                className="flex-1 py-3 bg-red-500 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2"
              >
                {deleting ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
