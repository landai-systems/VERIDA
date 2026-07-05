import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { auth, User, LoginPayload, RegisterPayload } from '../api/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  login: (p: LoginPayload) => Promise<void>
  register: (p: RegisterPayload) => Promise<void>
  logout: () => Promise<void>
  restoreSession: () => Promise<void>
  setUser: (u: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, _get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: async (p) => {
        const tokens = await auth.login(p)
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        const user = await auth.me()
        set({ user, accessToken: tokens.access_token, refreshToken: tokens.refresh_token, isAuthenticated: true })
      },

      register: async (p) => {
        await auth.register(p)
        // After registration, auto-login
        const tokens = await auth.login({ email: p.email, password: p.password })
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        const user = await auth.me()
        set({ user, accessToken: tokens.access_token, refreshToken: tokens.refresh_token, isAuthenticated: true })
      },

      logout: async () => {
        try { await auth.logout() } catch { /* ignore */ }
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      restoreSession: async () => {
        const token = localStorage.getItem('access_token')
        if (!token) return
        try {
          const user = await auth.me()
          set({ user, accessToken: token, isAuthenticated: true })
        } catch {
          set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
        }
      },

      setUser: (u) => set({ user: u }),
    }),
    { name: 'verida-auth', partialize: (s) => ({ accessToken: s.accessToken, refreshToken: s.refreshToken }) },
  ),
)

// Listen for forced logout (401 + no refresh)
window.addEventListener('auth:logout', () => {
  useAuthStore.getState().logout()
})
