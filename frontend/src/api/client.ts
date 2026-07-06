/**
 * Axios instance — auto-attaches JWT, auto-refreshes on 401.
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = ''

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach access token ───────────────────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: auto-refresh on 401 ─────────────────────────────
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((p) => {
    if (error) p.reject(error)
    else p.resolve(token!)
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`
        return apiClient(original)
      })
    }
    original._retry = true
    isRefreshing = true
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      isRefreshing = false
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.dispatchEvent(new Event('auth:logout'))
      return Promise.reject(error)
    }
    try {
      const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      })
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      processQueue(null, data.access_token)
      original.headers.Authorization = `Bearer ${data.access_token}`
      return apiClient(original)
    } catch (err) {
      processQueue(err, null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.dispatchEvent(new Event('auth:logout'))
      return Promise.reject(err)
    } finally {
      isRefreshing = false
    }
  },
)

export default apiClient
