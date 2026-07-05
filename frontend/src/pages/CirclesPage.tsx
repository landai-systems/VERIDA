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
    circlesApi.list()
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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-xl font-bold text-slate-900 dark:text-white">Circles</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition"
        >
          {showCreate ? 'Cancel' : '+ New Circle'}
        </button>
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-500 text-center">{error}</p>
      )}

      {showCreate && (
        <form onSubmit={create} className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
          <h2 className="font-semibold text-slate-800 dark:text-slate-200">Create Circle</h2>
          <input
            type="text"
            required
            value={createForm.name}
            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
            placeholder="Circle name"
            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            maxLength={80}
          />
          <input
            type="text"
            value={createForm.description}
            onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
            placeholder="Description (optional)"
            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={creating}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white rounded-xl text-sm font-medium transition"
          >
            {creating ? 'Creating…' : 'Create Circle'}
          </button>
        </form>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="No circles yet"
          description="Create a circle and invite close friends or family to share moments together."
          action={{ label: 'Create your first circle', onClick: () => setShowCreate(true) }}
        />
      ) : (
        <div className="space-y-4">
          {items.map((circle) => (
            <div key={circle.id} className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-semibold text-slate-800 dark:text-slate-200">{circle.name}</h2>
                  {circle.description && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{circle.description}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-1">
                    {circle.is_private ? '🔒 Private' : '🌐 Open'} · {circle.member_count ?? 0} members
                  </p>
                </div>
                <button
                  onClick={() => leave(circle.id)}
                  className="text-xs text-red-400 hover:text-red-600 transition"
                  aria-label="Leave circle"
                >
                  Leave
                </button>
              </div>

              {/* Invite */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inviteState[circle.id] ?? ''}
                  onChange={(e) => setInviteState({ ...inviteState, [circle.id]: e.target.value })}
                  placeholder="Invite by @handle"
                  className="flex-1 px-3 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  aria-label={`Invite to ${circle.name}`}
                />
                <button
                  onClick={() => invite(circle.id)}
                  className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
                >
                  Invite
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
