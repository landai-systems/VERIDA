import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { consent as consentApi, ConsentRecord } from '../api/consent'
import { gdpr as gdprApi } from '../api/gdpr'
import { useAuthStore } from '../store/authStore'

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [records, setRecords] = useState<ConsentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    consentApi.getConsent()
      .then(setRecords)
      .catch(() => setRecords([]))
      .finally(() => setLoading(false))
  }, [])

  const withdraw = async (type: string) => {
    if (!confirm(`Withdraw consent for "${type}"? Some features may stop working.`)) return
    try {
      await consentApi.withdrawConsent(type)
      setRecords((prev) => prev.map((r) => r.consent_type === type ? { ...r, withdrawn_at: new Date().toISOString() } : r))
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
    const confirmed = prompt('Type DELETE MY ACCOUNT to confirm permanent deletion:')
    if (confirmed !== 'DELETE MY ACCOUNT') return
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
    <div className="px-4 py-6 space-y-8">
      <h1 className="text-xl font-bold text-slate-900 dark:text-white pt-2">Settings</h1>

      {user && (
        <section className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800">
          <h2 className="font-semibold text-slate-800 dark:text-slate-200 mb-3">Account</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">{user.display_name} · @{user.handle}</p>
          <p className="text-sm text-slate-500 dark:text-slate-500">{user.email}</p>
          {!user.is_verified && (
            <p className="text-xs text-amber-500 mt-2">⚠ Email not verified — check your inbox.</p>
          )}
        </section>
      )}

      {/* Consent management */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200">Consent Management</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          You can withdraw consent at any time. Withdrawal doesn't delete your data — use GDPR Erasure below for that.
        </p>

        {loading ? (
          <div className="flex justify-center py-4">
            <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : records.length === 0 ? (
          <p className="text-sm text-slate-400">No consent records on file.</p>
        ) : (
          <div className="space-y-3">
            {records.map((r) => (
              <div key={r.id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium text-slate-700 dark:text-slate-300 capitalize">{r.consent_type.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-slate-400">
                    {r.withdrawn_at ? '🚫 Withdrawn' : '✓ Active'} · v{r.version}
                  </p>
                </div>
                {!r.withdrawn_at && (
                  <button
                    onClick={() => withdraw(r.consent_type)}
                    className="text-xs text-red-400 hover:text-red-600 transition"
                  >
                    Withdraw
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* GDPR */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
        <h2 className="font-semibold text-slate-800 dark:text-slate-200">Your Data Rights (GDPR)</h2>

        {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
        {message && <p role="status" className="text-sm text-emerald-500">{message}</p>}

        <button
          onClick={exportData}
          disabled={exporting}
          className="w-full py-3 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium transition disabled:opacity-60"
        >
          {exporting ? 'Preparing export…' : '⬇ Export My Data (Article 20)'}
        </button>

        <button
          onClick={deleteAccount}
          disabled={deleting}
          className="w-full py-3 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 rounded-xl text-sm font-medium transition disabled:opacity-60"
        >
          {deleting ? 'Deleting…' : '🗑 Delete Account & All Data (Article 17)'}
        </button>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Account deletion is permanent and irreversible. All your data will be erased within 30 days.
        </p>
      </section>

      {/* Sign out */}
      <button
        onClick={async () => { await logout(); navigate('/login', { replace: true }) }}
        className="w-full py-3 text-slate-500 dark:text-slate-400 text-sm hover:text-slate-700 dark:hover:text-slate-200 transition"
      >
        Sign out
      </button>
    </div>
  )
}
