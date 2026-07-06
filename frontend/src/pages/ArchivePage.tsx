import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { profile as profileApi } from '../api/profile'
import { Post } from '../api/feed'
import EmptyState from '../components/EmptyState'

type MonthGroup = { label: string; key: string; posts: Post[] }

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
      const label = new Date(Number(year), Number(month) - 1).toLocaleDateString(undefined, {
        month: 'long',
        year: 'numeric',
      })
      return { label, key, posts: ps }
    })
}

export default function ArchivePage() {
  const user = useAuthStore((s) => s.user)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Post | null>(null)

  useEffect(() => {
    if (!user) return
    profileApi
      .getPosts(user.id)
      .then((data) => setPosts(Array.isArray(data) ? data : (data as { posts: Post[] })?.posts ?? []))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false))
  }, [user])

  const groups = groupByMonth(posts)

  return (
    <div className="px-4 py-6 pb-32">
      <div className="pt-2 mb-6">
        <h1 className="text-2xl font-bold text-white">Your Authentic Year</h1>
        <p className="text-sm text-slate-500 mt-1">Every moment you shared, exactly as it was.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" aria-label="Loading" />
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          emoji="📚"
          title="Your archive is empty"
          description="Moments you capture will be stored here permanently — a real record of your days."
        />
      ) : (
        <div className="space-y-8">
          {groups.map(({ label, key, posts: monthPosts }) => (
            <section key={key}>
              {/* Sticky month header */}
              <div className="sticky top-0 z-10 bg-[#080810]/90 backdrop-blur-md py-2 mb-3 -mx-4 px-4 border-b border-white/[0.04]">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {label} · {monthPosts.length} moment{monthPosts.length !== 1 ? 's' : ''}
                </h2>
              </div>

              {/* 3-col grid */}
              <div className="grid grid-cols-3 gap-1.5">
                {monthPosts.map((post) => (
                  <button
                    key={post.id}
                    onClick={() => setSelected(post)}
                    className="aspect-square bg-white/[0.04] rounded-xl overflow-hidden hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-[#080810]"
                    aria-label={post.caption ?? `Moment from ${new Date(post.published_at).toLocaleDateString()}`}
                  >
                    {post.media_url ? (
                      <img
                        src={post.media_url}
                        alt={post.caption ?? ''}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center p-2 text-xs text-slate-400 text-center leading-tight">
                        {post.caption?.slice(0, 60) ?? '—'}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {/* Lightbox modal */}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
          role="dialog"
          aria-modal="true"
          onClick={() => setSelected(null)}
        >
          <div
            className="relative max-w-sm w-full bg-white/5 border border-white/[0.08] rounded-3xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {selected.media_url && (
              <img
                src={selected.media_url}
                alt={selected.caption ?? ''}
                className="w-full aspect-[4/5] object-cover"
              />
            )}
            {selected.caption && (
              <div className="px-5 py-4">
                <p className="text-sm text-slate-300">{selected.caption}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {new Date(selected.published_at).toLocaleDateString(undefined, {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </p>
              </div>
            )}
            <button
              onClick={() => setSelected(null)}
              className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/70 transition-colors"
              aria-label="Close"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
