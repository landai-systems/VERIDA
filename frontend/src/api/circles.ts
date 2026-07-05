import apiClient from './client'

export interface Circle { id: string; name: string; description: string; owner_id: string; is_private: boolean; member_count: number }
export interface CreateCirclePayload { name: string; description?: string; is_private?: boolean }

export const circles = {
  list: () => apiClient.get<Circle[]>('/circles').then(r => r.data),
  create: (p: CreateCirclePayload) => apiClient.post<Circle>('/circles', p).then(r => r.data),
  get: (id: string) => apiClient.get<Circle>(`/circles/${id}`).then(r => r.data),
  update: (id: string, p: Partial<CreateCirclePayload>) => apiClient.put<Circle>(`/circles/${id}`, p).then(r => r.data),
  delete: (id: string) => apiClient.delete(`/circles/${id}`).then(r => r.data),
  invite: (id: string, handle: string) => apiClient.post(`/circles/${id}/invite`, { handle }).then(r => r.data),
  accept: (id: string) => apiClient.post(`/circles/${id}/accept`).then(r => r.data),
  leave: (id: string, userId: string) => apiClient.delete(`/circles/${id}/members/${userId}`).then(r => r.data),
}
