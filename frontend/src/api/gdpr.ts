import apiClient from './client'

export const gdpr = {
  exportData: () => apiClient.post('/gdpr/export', {}, { responseType: 'blob' }).then(r => r.data),
  deleteAccount: () => apiClient.delete('/gdpr/me', { data: { confirm: 'DELETE MY ACCOUNT' } }).then(r => r.data),
}
