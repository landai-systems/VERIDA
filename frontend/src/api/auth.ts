import apiClient from './client'

export interface LoginPayload { email: string; password: string }
export interface RegisterPayload { handle: string; email: string; password: string; display_name: string; consent: boolean }
export interface AuthResponse { access_token: string; refresh_token: string; token_type: string }
export interface User { id: string; handle: string; email: string; display_name: string; bio: string; avatar_url: string | null; is_verified: boolean }

export const auth = {
  login: (p: LoginPayload) => apiClient.post<AuthResponse>('/auth/login', p).then(r => r.data),
  register: (p: RegisterPayload) => apiClient.post<{ user: User }>('/auth/register', p).then(r => r.data),
  refresh: (refresh_token: string) => apiClient.post<AuthResponse>('/auth/refresh', { refresh_token }).then(r => r.data),
  logout: () => apiClient.post('/auth/logout').then(r => r.data),
  me: () => apiClient.get<User>('/auth/me').then(r => r.data),
}
