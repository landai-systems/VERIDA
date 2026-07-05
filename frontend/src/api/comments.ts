import apiClient from './client'

export interface Comment { id: string; author_id: string; author_handle: string; body: string; created_at: string }

export const comments = {
  list: (postId: string) => apiClient.get<Comment[]>(`/posts/${postId}/comments`).then(r => r.data),
  add: (postId: string, body: string) => apiClient.post<Comment>(`/posts/${postId}/comments`, { body }).then(r => r.data),
  delete: (postId: string, commentId: string) => apiClient.delete(`/posts/${postId}/comments/${commentId}`).then(r => r.data),
}
