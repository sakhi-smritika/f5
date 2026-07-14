import { supabase } from './supabase'

const backendUrl = import.meta.env.VITE_BACKEND_URL ?? ''

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const headers = new Headers(options.headers)
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }
  // Let the browser set the multipart boundary for FormData bodies; only
  // default to JSON for other (string) bodies.
  const isFormData =
    typeof FormData !== 'undefined' && options.body instanceof FormData
  if (!headers.has('Content-Type') && options.body && !isFormData) {
    headers.set('Content-Type', 'application/json')
  }

  const url = backendUrl ? `${backendUrl}${path}` : path
  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    await supabase.auth.signOut()
    throw new Error('Unauthorized')
  }

  return response
}
