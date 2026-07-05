import { create } from 'zustand'
import { feed as feedApi, Post } from '../api/feed'

interface FeedState {
  posts: Post[]
  cursor: string | null
  hasMore: boolean
  hasMomentToday: boolean
  loading: boolean
  error: string | null
  fetchFeed: () => Promise<void>
  fetchMore: () => Promise<void>
  addPost: (p: Post) => void
  updatePostReaction: (postId: string, emoji: string, added: boolean) => void
  reset: () => void
}

export const useFeedStore = create<FeedState>((set, get) => ({
  posts: [],
  cursor: null,
  hasMore: false,
  hasMomentToday: false,
  loading: false,
  error: null,

  fetchFeed: async () => {
    set({ loading: true, error: null })
    try {
      const data = await feedApi.getFeed()
      set({ posts: data.posts, cursor: data.cursor, hasMore: data.has_more, hasMomentToday: data.has_moment_today, loading: false })
    } catch {
      set({ error: 'Failed to load feed', loading: false })
    }
  },

  fetchMore: async () => {
    const { cursor, loading, hasMore, posts } = get()
    if (!hasMore || loading) return
    set({ loading: true })
    try {
      const data = await feedApi.getFeed(cursor ?? undefined)
      set({ posts: [...posts, ...data.posts], cursor: data.cursor, hasMore: data.has_more, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  addPost: (p) => set((s) => ({ posts: [p, ...s.posts], hasMomentToday: true })),

  updatePostReaction: (postId, emoji, added) => {
    set((s) => ({
      posts: s.posts.map((p) => {
        if (p.id !== postId) return p
        const my_reactions = added
          ? [...p.my_reactions, emoji]
          : p.my_reactions.filter((e) => e !== emoji)
        return { ...p, my_reactions }
      }),
    }))
  },

  reset: () => set({ posts: [], cursor: null, hasMore: false, hasMomentToday: false }),
}))
