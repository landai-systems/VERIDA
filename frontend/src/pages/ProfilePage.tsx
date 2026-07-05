import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { profile as profileApi, Streak } from '../api/profile'
import { useAuthStore } from '../store/authStore'
import StreakBadge from '../components/StreakBadge'
import EmptyState from '../components/EmptyState'
import { Post } from '../api/feed'

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const [streak, setStreak] = useState<Streak | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    Promise.all([
      profileApi.getStreak().catch(() => null),
      profileApi.getPosts(user.id).catch(() => []),
    ]).then(([s, p]) => {
      setStreak(s)
      setPosts(Array.isArray(p) ? p : p?.posts ?? [])
    }).finally(() => setLoading(false))
  }, [user])

  if (!user) return null

  // Archive grid — last 12 posts
  const archivePreview = posts.slice(0, 12)

  return (
    <div className="px-4 py-6 space-y-6">
      {/* Avatar + name */}
      <div className="flex items-center gap-4 pt-2">
        <div className="w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-2xl font-bold text-indigo-600 dark:text-indigo-400 overflow-hidden flex-shrink-0">
          {user.avatar_url ? (
            <img src={user.avatar_url} alt={user.display_name} className="w-full h-full object-cover" />
          ) : (
            user.display_name.slice(0, 2).toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-slate-900 dark:text-white truncate">{user.display_name}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">@{user.handle}</p>
          {user.bio && <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{user.bio}</p>}
        </div>
      </div>

      {/* Streak */}
      {streak && streak.current_streak > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-2xl p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-amber-700 dark:text-amber-300">Current streak</p>
            <p className="text-xs text-amber-500 dark:text-amber-400 mt-0.5">
              Longest: {streak.longest_streak} days — keep going at your own pace.
            </p>
          </div>
          <StreakBadge count={streak.current_streak} size="md" />
        </div>
      )}

      {/* Quick links */}
      <div className="flex gap-3">
        <Link
          to="/archive"
          className="flex-1 py-2.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium text-center hover:bg-slate-200 dark:hover:bg-slate-700 transition"
        >
          Your Archive
        </Link>
        <Link
          to="/settings"
          className="flex-1 py-2.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-medium text-center hover:bg-slate-200 dark:hover:bg-slate-700 transition"
        >
          Settings
        </Link>
      </div>

      {/* Authentic Year archive grid */}
      <section aria-labelledby="archive-heading">
        <h2 id="archive-heading" className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3">
          Your Authentic Year
        </h2>
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : archivePreview.length === 0 ? (
          <EmptyState
            title="No moments yet"
            description="Start capturing daily moments to build your authentic year archive."
          />
        ) : (
          <div className="grid grid-cols-3 gap-1.5">
            {archivePreview.map((post) => (
              <div key={post.id} className="aspect-square bg-slate-200 dark:bg-slate-800 rounded-xl overflow-hidden relative">
                {post.media_url ? (
                  <img src={post.media_url} alt={post.caption} className="w-full h-full object-cover" loading="lazy" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-500 text-xs p-2 text-center">
                    {post.caption?.slice(0, 30)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {posts.length > 12 && (
          <Link
            to="/archive"
            className="block text-center text-sm text-indigo-600 dark:text-indigo-400 mt-3 hover:underline"
          >
            View all {posts.length} moments →
          </Link>
        )}
      </section>
    </div>
  )
}
