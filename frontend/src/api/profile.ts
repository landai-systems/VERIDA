import apiClient from './client'

export interface Profile { id: string; handle: string; display_name: string; bio: string; avatar_url: string | null; is_verified: boolean }
export interface Streak { current_streak: number; longest_streak: number }
export interface UpdateProfilePayload { display_name?: string; bio?: string; avatar_url?: string }

export const profile = {
  getProfile: () => apiClient.get<Profile>('/auth/me').then(r => r.data),
  updateProfile: (p: UpdateProfilePayload) => apiClient.put<Profile>('/auth/me', p).then(r => r.data),
  getStreak: () => apiClient.get<Streak>('/me/streak').then(r => r.data),
  getPosts: (userId: string) => apiClient.get(`/posts?author_id=${userId}`).then(r => r.data),
}
