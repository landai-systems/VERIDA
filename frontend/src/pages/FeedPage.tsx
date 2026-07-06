import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFeedStore } from '../store/feedStore'
import PostCard from '../components/PostCard'
import EmptyState from '../components/EmptyState'
import SessionNudge from '../components/SessionNudge'
import { useAuthStore } from '../store/authStore'

const SESSION_LIMIT_MS = 10 * 60 * 1000 // 10 minutes

export default function FeedPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const { posts, hasMore, loading, error, hasMomentToday, fetchFeed, fetchMore } = useFeedStore()
  const [showNudge, setShowNudge] = useState(false)
  const nudgeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    fetchFeed()
  }, [fetchFeed])

  // Session-end nudge after 10 min
  useEffect(() => {
    nudgeTimer.current = setTimeout(() => setShowNudge(true), SESSION_LIMIT_MS)
    return () => {
      if (nudgeTimer.current) clearTimeout(nudgeTimer.current)
    }
  }, [])

  const dismissNudge = () => {
    setShowNudge(false)
    if (nudgeTimer.current) clearTimeout(nudgeTimer.current)
    nudgeTimer.current = setTimeout(() => setShowNudge(true), SESSION_LIMIT_MS)
  }

  // Infinite scroll
  useEffect(() => {
    const sentinel = document.getElementById('feed-sentinel')
    if (!sentinel) return
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) fetchMore()
      },
      { threshold: 0.1 },
    )
    obs.observe(sentinel)
    return () => obs.disconnect()
  }, [hasMore, loading, fetchMore])

  const avatarInitials = user?.display_name?.slice(0, 2).toUpperCase() ?? 'ME'

  // Reciprocity gate
  if (!hasMomentToday && posts.length === 0 && !loading) {
    return (
      <div className="relative min-h-screen flex items-center justify-center px-4 py-12 overflow-hidden">
        {/* Blurred bg */}
        <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/20 to-[#080810]" />

        <div className="relative z-10 w-full max-w-sm text-center">
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-3xl p-10 shadow-[0_0_40px_rgba(99,102,241,0.15)]">
            <div className="text-6xl mb-5 select-none">📸</div>
            <h2 className="text-2xl font-bold text-white mb-3">Post your moment to unlock the feed</h2>
            <p className="text-slate-400 text-sm leading-relaxed mb-8 max-w-xs mx-auto">
              VERIDA unlocks the feed after you share your daily moment. It keeps things mutual and authentic.
            </p>
            <button
              onClick={() => navigate('/capture')}
              className="bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-600 hover:to-violet-700 text-white font-semibold py-4 px-8 rounded-2xl w-full transition-all duration-200 text-lg shadow-[0_0_30px_rgba(99,102,241,0.3)] flex items-center justify-center gap-3"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Capture Today's Moment
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen">
      {showNudge && <SessionNudge onDismiss={dismissNudge} />}

      {/* Sticky header */}
      <header className="sticky top-0 z-30 bg-[#080810]/80 backdrop-blur-xl border-b border-white/[0.06] px-4 h-14 flex items-center justify-between">
        <span className="text-xl font-black text-white tracking-tight">VERIDA</span>

        {/* Capture button (center) */}
        <button
          onClick={() => navigate('/capture')}
          className="absolute left-1/2 -translate-x-1/2 w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-[0_0_16px_rgba(99,102,241,0.4)] hover:shadow-[0_0_24px_rgba(99,102,241,0.6)] transition-all duration-200"
          aria-label="Capture moment"
        >
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        {/* Avatar */}
        <button
          onClick={() => navigate('/profile')}
          className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500/40 to-violet-600/40 border border-white/10 flex items-center justify-center text-xs font-bold text-white overflow-hidden"
          aria-label="Profile"
        >
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt={user.display_name} className="w-full h-full object-cover" />
          ) : (
            avatarInitials
          )}
        </button>
      </header>

      {/* Feed */}
      <div className="flex-1 px-4 py-4 space-y-4">
        {error && (
          <p role="alert" className="text-sm text-red-400 text-center py-4 bg-red-500/10 rounded-2xl border border-red-500/20">
            {error}
          </p>
        )}

        {!loading && posts.length === 0 ? (
          <EmptyState
            emoji="🌟"
            title="Nothing here yet"
            description="When people in your circles share moments, they'll appear here."
            action={{ label: 'Manage Circles', onClick: () => navigate('/circles') }}
          />
        ) : (
          <div className="space-y-4">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}

            {/* Sentinel */}
            <div id="feed-sentinel" aria-hidden="true" />

            {/* Loading */}
            {loading && (
              <div className="flex justify-center py-6" role="status" aria-label="Loading more posts">
                <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {/* End of feed */}
            {!hasMore && !loading && posts.length > 0 && (
              <div className="flex flex-col items-center py-12 gap-2 text-center">
                <div className="text-4xl select-none">🌿</div>
                <p className="text-white font-medium">You're all caught up!</p>
                <p className="text-slate-500 text-sm">Come back tomorrow for more moments.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
