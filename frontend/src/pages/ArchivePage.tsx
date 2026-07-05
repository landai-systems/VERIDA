import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { profile as profileApi } from '../api/profile'
import { Post } from '../api/feed'
import EmptyState from '../components/EmptyState'

type MonthGroup = { label: string; posts: Post[] }

function groupByMonth(posts: Post[]): MonthGroup[] {
  const map = new Map<string, Post[]>()
  posts.forEach((p) => {
    const d = new Date(p.published_at)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(p)
  })
  return Array.from(map.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([key, ps]) => {
      const [year, month] = key.split('-')
      const label = new Date(Number(year), Number(month) - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
      return { label, posts: ps }
    })
}

export default function ArchivePage() {
  const user = useAuthStore((s) => s.user)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    profileApi.getPosts(user.id)
      .then((data) => setPosts(Array.isArray(data) ? data : data?.posts ?? []))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false))
  }, [user])

  const groups = groupByMonth(posts)

  return (
    <div className="px-4 py-6 space-y-8">
      <h1 className="text-xl font-bold text-slate-900 dark:text-white pt-2">Your Authentic Year</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 -mt-4">
        Every moment you shared, exactly as it was.
      </p>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" aria-label="Loading" />
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          title="Your archive is empty"
          description="Moments you capture will be stored here permanently — a real record of your days."
        />
      ) : (
        groups.map(({ label, posts: monthPosts }) => (
          <section key={label} aria-labelledby={`month-${label}`}>
            <h2 id={`month-${label}`} className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
              {label}
            </h2>
            <div className="grid grid-cols-3 gap-1.5">
              {monthPosts.map((post) => (
                <div key={post.id} className="aspect-square bg-slate-200 dark:bg-slate-800 rounded-xl overflow-hidden">
                  {post.media_url ? (
                    <img src={post.media_url} alt={post.caption} className="w-full h-full object-cover" loading="lazy" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center p-2 text-xs text-slate-500 text-center leading-tight">
                      {post.caption?.slice(0, 50) ?? '—'}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  )
}
