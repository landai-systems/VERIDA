import apiClient from './client'

export interface Post {
  id: string
  author_id: string
  author_handle: string
  author_display_name: string
  author_avatar_url: string | null
  caption: string
  media_url: string
  is_late: boolean
  published_at: string
  attestation_status: 'pending' | 'passed' | 'failed'
  my_reactions: string[]
}

export interface FeedResponse {
  posts: Post[]
  cursor: string | null
  has_more: boolean
  has_moment_today: boolean
}

export const feed = {
  getFeed: (cursor?: string) =>
    apiClient.get<FeedResponse>('/feed', { params: cursor ? { cursor } : {} }).then(r => r.data),
}
