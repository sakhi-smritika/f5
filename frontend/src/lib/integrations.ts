import { apiFetch } from './api'

export type GoogleConnectionStatus = {
  connected: boolean
  google_email: string | null
  connected_at?: string | null
}

export async function getGoogleConnectionStatus(): Promise<GoogleConnectionStatus> {
  const response = await apiFetch('/api/v1/integrations/google/status')
  if (!response.ok) {
    throw new Error('Failed to load Google connection status')
  }
  return (await response.json()) as GoogleConnectionStatus
}

export async function getGoogleAuthorizeUrl(): Promise<string> {
  const response = await apiFetch('/api/v1/integrations/google/authorize')
  if (!response.ok) {
    throw new Error('Failed to start Google connection')
  }
  const data = (await response.json()) as { url?: string }
  if (!data.url) {
    throw new Error('Missing Google authorization URL')
  }
  return data.url
}

export async function disconnectGoogle(): Promise<void> {
  const response = await apiFetch('/api/v1/integrations/google', { method: 'DELETE' })
  if (!response.ok && response.status !== 204) {
    throw new Error('Failed to disconnect Google')
  }
}
