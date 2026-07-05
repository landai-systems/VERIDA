import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFeedStore } from '../store/feedStore'
import PostCard from '../components/PostCard'
import EmptyState from '../components/EmptyState'
import SessionNudge from '../components/SessionNudge'

const SESSION_LIMIT_MS = 10 * 60 * 1000 // 10 minutes

export default function FeedPage() {
  const navigate = useNavigate()
  const { posts, hasMore, loading, error, hasMomentToday, fetchFeed, fetchMore } = useFeedStore()
  const [showNudge, setShowNudge] = useState(false)
  const sessionStart = useRef(Date.now())
  const nudgeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    fetchFeed()
  }, [fetchFeed])

  // Session-end nudge after 10 min
  useEffect(() => {
    nudgeTimer.current = setTimeout(() => setShowNudge(true), SESSION_LIMIT_MS)
    return () => { if (nudgeTimer.current) clearTimeout(nudgeTimer.current) }
  }, [])

  // Dismiss clears timer
  const dismissNudge = () => {
    setShowNudge(false)
    // Re-arm for another 10 min
    if (nudgeTimer.current) clearTimeout(nudgeTimer.current)
    nudgeTimer.current = setTimeout(() => setShowNudge(true), SESSION_LIMIT_MS)
    void sessionStart
  }

  // Infinite scroll
  useEffect(() => {
    const sentinel = document.getElementById('feed-sentinel')
    if (!sentinel) return
    const obs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !loading) fetchMore()
    }, { threshold: 0.1 })
    obs.observe(sentinel)
    return () => obs.disconnect()
  }, [hasMore, loading, fetchMore])

  // Reciprocity gate
  if (!hasMomentToday && posts.length === 0 && !loading) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-screen gap-6 text-center">
        <div className="text-6xl">📸</div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Post your moment first</h2>
        <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs">
          VERIDA unlocks the feed after you share your daily moment. It keeps things mutual and authentic.
        </p>
        <button
          onClick={() => navigate('/capture')}
          className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold transition"
        >
          Capture Today's Moment
        </button>
      </div>
    )
  }

  return (
    <div className="px-4 py-6 space-y-4">
      {showNudge && <SessionNudge onDismiss={dismissNudge} />}

      <h1 className="text-xl font-bold text-slate-900 dark:text-white">Your Feed</h1>

      {error && (
        <p role="alert" className="text-sm text-red-500 text-center py-4">{error}</p>
      )}

      {!loading && posts.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          description="When people in your circles share moments, they'll appear here."
          action={{ label: 'Manage Circles', onClick: () => navigate('/circles') }}
        />
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}

          {/* Sentinel for infinite scroll */}
          <div id="feed-sentinel" aria-hidden="true" />

          {/* Loading */}
          {loading && (
            <div className="flex justify-center py-4" role="status" aria-label="Loading more posts">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* End of feed */}
          {!hasMore && !loading && posts.length > 0 && (
            <div className="flex flex-col items-center py-8 gap-2 text-center">
              <div className="text-3xl">🌿</div>
              <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">You're all caught up!</p>
              <p className="text-slate-400 dark:text-slate-500 text-xs">Come back tomorrow for more moments.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
