import { useEffect, useState } from 'react'
import { circles as circlesApi, Circle } from '../api/circles'
import EmptyState from '../components/EmptyState'

export default function CirclesPage() {
  const [items, setItems] = useState<Circle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', description: '' })
  const [creating, setCreating] = useState(false)
  const [inviteState, setInviteState] = useState<Record<string, string>>({})

  useEffect(() => {
    circlesApi
      .list()
      .then(setItems)
      .catch(() => setError('Failed to load circles'))
      .finally(() => setLoading(false))
  }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    try {
      const c = await circlesApi.create(createForm)
      setItems([...items, c])
      setShowCreate(false)
      setCreateForm({ name: '', description: '' })
    } catch {
      setError('Failed to create circle')
    } finally {
      setCreating(false)
    }
  }

  const invite = async (circleId: string) => {
    const handle = inviteState[circleId]?.trim()
    if (!handle) return
    try {
      await circlesApi.invite(circleId, handle)
      setInviteState({ ...inviteState, [circleId]: '' })
    } catch {
      setError('Invite failed — check the handle and try again.')
    }
  }

  const leave = async (circleId: string) => {
    if (!confirm('Leave this circle?')) return
    try {
      await circlesApi.delete(circleId)
      setItems(items.filter((c) => c.id !== circleId))
    } catch {
      setError('Failed to leave circle')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen" role="status">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" aria-label="Loading" />
      </div>
    )
  }

  return (
    <div className="px-4 py-6 space-y-5 pb-32">
      {/* Header */}
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-2xl font-bold text-white">Circles</h1>
      </div>

      {error && (
        <div role="alert" className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl px-4 py-3 text-sm text-center">
          {error}
        </div>
      )}

      {/* Circle list */}
      {items.length === 0 ? (
        <EmptyState
          emoji="⭕"
          title="No circles yet"
          description="Create a circle and invite close friends or family to share moments together."
          action={{ label: 'Create your first circle', onClick: () => setShowCreate(true) }}
        />
      ) : (
        <div className="space-y-3">
          {items.map((circle) => (
            <div
              key={circle.id}
              className="bg-white/5 border border-white/[0.08] rounded-2xl p-5 space-y-4 hover:border-white/[0.12] transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Avatar stack placeholder */}
                  <div className="flex -space-x-2 mb-2">
                    {Array.from({ length: Math.min(circle.member_count ?? 0, 4) }).map((_, i) => (
                      <div
                        key={i}
                        className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500/50 to-violet-600/50 border-2 border-[#080810] flex items-center justify-center text-xs text-white font-bold"
                      >
                        {String.fromCharCode(65 + i)}
                      </div>
                    ))}
                    {(circle.member_count ?? 0) > 4 && (
                      <div className="w-8 h-8 rounded-full bg-white/10 border-2 border-[#080810] flex items-center justify-center text-xs text-slate-400">
                        +{(circle.member_count ?? 0) - 4}
                      </div>
                    )}
                  </div>
                  <h2 className="font-semibold text-white">{circle.name}</h2>
                  {circle.description && (
                    <p className="text-xs text-slate-400 mt-0.5">{circle.description}</p>
                  )}
                  <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                    <span>{circle.is_private ? '🔒' : '🌐'}</span>
                    {circle.is_private ? 'Private' : 'Open'} · {circle.member_count ?? 0} members
                  </p>
                </div>
                <button
                  onClick={() => leave(circle.id)}
                  className="text-xs text-red-400/70 hover:text-red-400 transition-colors flex-shrink-0"
                  aria-label="Leave circle"
                >
                  Leave
                </button>
              </div>

              {/* Invite input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inviteState[circle.id] ?? ''}
                  onChange={(e) => setInviteState({ ...inviteState, [circle.id]: e.target.value })}
                  placeholder="Invite by @handle"
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  aria-label={`Invite to ${circle.name}`}
                  onKeyDown={(e) => e.key === 'Enter' && invite(circle.id)}
                />
                <button
                  onClick={() => invite(circle.id)}
                  className="px-4 py-2 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white rounded-xl text-sm font-medium transition-all duration-150"
                >
                  Invite
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* FAB */}
      <button
        onClick={() => setShowCreate(true)}
        className="fixed bottom-24 right-4 w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white text-2xl flex items-center justify-center shadow-[0_0_24px_rgba(99,102,241,0.4)] hover:shadow-[0_0_32px_rgba(99,102,241,0.6)] transition-all duration-200 z-40"
        aria-label="Create new circle"
      >
        +
      </button>

      {/* Create circle sheet */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-end justify-center" role="dialog" aria-modal="true" aria-label="Create circle">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowCreate(false)}
            aria-hidden="true"
          />
          <div className="relative w-full max-w-lg backdrop-blur-xl bg-[#0d0d1a] border border-white/10 rounded-t-3xl p-6 space-y-5 shadow-[0_-10px_40px_rgba(0,0,0,0.5)] animate-[slideUp_0.3s_ease-out]">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Create Circle</h2>
              <button
                onClick={() => setShowCreate(false)}
                className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/20 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={create} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">Circle Name</label>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  placeholder="e.g. Family, Close Friends"
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full text-sm transition-colors"
                  maxLength={80}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-wide">Description</label>
                <input
                  type="text"
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  placeholder="Optional description"
                  className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 w-full text-sm transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={creating}
                className="w-full py-3 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 disabled:opacity-60 text-white rounded-xl font-semibold transition-all duration-200 flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Creating…
                  </>
                ) : (
                  'Create Circle'
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
