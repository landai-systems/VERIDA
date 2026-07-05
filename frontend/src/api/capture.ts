import apiClient from './client'

export interface CaptureToken { capture_token: string; moment_id: string; expires_at: string }

export const capture = {
  initiate: () => apiClient.post<CaptureToken>('/capture/initiate').then(r => r.data),
  submit: (captureToken: string, form: FormData) =>
    apiClient.post('/capture/submit', form, {
      headers: { 'Content-Type': 'multipart/form-data', 'X-Capture-Token': captureToken },
    }).then(r => r.data),
}
