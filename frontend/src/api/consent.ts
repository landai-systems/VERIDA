import apiClient from './client'

export interface ConsentRecord { id: string; consent_type: string; version: string; granted_at: string; withdrawn_at: string | null }
export interface RecordConsentPayload { consent_type: string; version: string; text: string }

export const consent = {
  getConsent: () => apiClient.get<ConsentRecord[]>('/consent').then(r => r.data),
  recordConsent: (p: RecordConsentPayload) => apiClient.post<ConsentRecord>('/consent', p).then(r => r.data),
  withdrawConsent: (consent_type: string) => apiClient.post('/consent/withdraw', { consent_type }).then(r => r.data),
}
