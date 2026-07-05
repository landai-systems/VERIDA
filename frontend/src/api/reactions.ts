import apiClient from './client'

export const reactions = {
  add: (postId: string, emoji: string) =>
    apiClient.post(`/posts/${postId}/reactions`, { emoji }).then(r => r.data),
  remove: (postId: string, emoji: string) =>
    apiClient.delete(`/posts/${postId}/reactions`, { data: { emoji } }).then(r => r.data),
}
