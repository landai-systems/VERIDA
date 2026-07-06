import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { profile as profileApi, Streak } from '../api/profile'
import { useAuthStore } from '../store/authStore'
import StreakBadge from '../components/StreakBadge'
import EmptyState from '../components/EmptyState'
import { Post } from '../api/feed'

// Build calendar heatmap: last 365 days, with post markers
function buildHeatmap(posts: Post[]) {
  const postDates = new Set(
    posts.map((p) => new Date(p.published_at).toISOString().slice(0, 10)),
  )
  const days: { date: string; hasPost: boolean }[] = []
  const today = new Date()
  for (let i = 364; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().slice(0, 10)
    days.push({ date: dateStr, hasPost: postDates.has(dateStr) })
  }
  return days
}

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
      setPosts(Array.isArray(p) ? p : (p as { posts: Post[] })?.posts ?? [])
    }).finally(() => setLoading(false))
  }, [user])

  if (!user) return null

  const heatmap = buildHeatmap(posts)
  const latestPost = posts[0]
  const postCount = posts.length
  const circleCount = 0 // not exposed in current API — placeholder

  return (
    <div className="flex flex-col min-h-screen pb-32">
      {/* Hero: blurred background from latest post */}
      <div className="relative h-48 flex-shrink-0 overflow-hidden">
        {latestPost?.media_url ? (
          <>
            <img
              src={latestPost.media_url}
              alt=""
              className="absolute inset-0 w-full h-full object-cover"
              aria-hidden="true"
            />
            <div className="absolute inset-0 bg-black/50 backdrop-blur-md" />
          </>
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/40 to-violet-900/20" />
        )}

        {/* Avatar overlaid */}
        <div className="absolute -bottom-10 left-4">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500/60 to-violet-600/60 border-4 border-[#080810] flex items-center justify-center text-2xl font-bold text-white overflow-hidden">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt={user.display_name} className="w-full h-full object-cover" />
            ) : (
              user.display_name.slice(0, 2).toUpperCase()
            )}
          </div>
        </div>
      </div>

      {/* Profile info */}
      <div className="px-4 pt-12 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-white truncate">{user.display_name}</h1>
            <p className="text-sm text-slate-500">@{user.handle}</p>
            {user.bio && <p className="text-sm text-slate-400 mt-1 leading-relaxed">{user.bio}</p>}
          </div>
          {streak && streak.current_streak > 0 && (
            <StreakBadge count={streak.current_streak} size="md" />
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Posts', value: postCount },
            { label: 'Streak', value: streak ? `${streak.current_streak}d` : '—' },
            { label: 'Circles', value: circleCount },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="bg-white/5 border border-white/[0.08] rounded-2xl p-3 text-center"
            >
              <p className="text-xl font-bold text-white">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        {/* Quick links */}
        <div className="flex gap-3">
          <Link
            to="/archive"
            className="flex-1 py-2.5 bg-white/5 border border-white/[0.08] text-slate-300 rounded-xl text-sm font-medium text-center hover:bg-white/[0.08] transition-colors"
          >
            Archive
          </Link>
          <Link
            to="/settings"
            className="flex-1 py-2.5 bg-white/5 border border-white/[0.08] text-slate-300 rounded-xl text-sm font-medium text-center hover:bg-white/[0.08] transition-colors"
          >
            Settings
          </Link>
        </div>

        {/* Authentic Year heatmap */}
        <section>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Your Authentic Year</h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : posts.length === 0 ? (
            <EmptyState
              emoji="📅"
              title="No moments yet"
              description="Start capturing daily moments to build your authentic year archive."
            />
          ) : (
            <div className="overflow-x-auto pb-2">
              <div
                className="grid gap-[3px]"
                style={{ gridTemplateColumns: 'repeat(52, minmax(0, 1fr))', minWidth: '320px' }}
                aria-label="Activity heatmap"
              >
                {heatmap.map(({ date, hasPost }) => (
                  <div
                    key={date}
                    title={date}
                    className={`aspect-square rounded-[2px] transition-colors ${
                      hasPost
                        ? 'bg-indigo-500'
                        : 'bg-white/[0.04]'
                    }`}
                  />
                ))}
              </div>
              <div className="flex items-center gap-2 mt-2 justify-end">
                <span className="text-xs text-slate-600">Less</span>
                <div className="w-3 h-3 rounded-sm bg-white/[0.04]" />
                <div className="w-3 h-3 rounded-sm bg-indigo-500/40" />
                <div className="w-3 h-3 rounded-sm bg-indigo-500" />
                <span className="text-xs text-slate-600">More</span>
              </div>
            </div>
          )}
        </section>

        {/* Photo grid preview */}
        {posts.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Recent Moments</h2>
              <Link to="/archive" className="text-xs text-indigo-400 hover:text-indigo-300">
                View all →
              </Link>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {posts.slice(0, 9).map((post) => (
                <div
                  key={post.id}
                  className="aspect-square bg-white/[0.04] rounded-xl overflow-hidden"
                >
                  {post.media_url ? (
                    <img
                      src={post.media_url}
                      alt={post.caption ?? ''}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center p-2 text-xs text-slate-500 text-center leading-tight">
                      {post.caption?.slice(0, 30)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
