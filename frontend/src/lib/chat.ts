import { apiFetch } from './api'
import { supabase } from './supabase'

export type ChatRole = 'user' | 'assistant'

export type ChatAttachment = {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  url?: string
}

export type ChatMessage = {
  role: ChatRole
  text: string
  event_id?: string
  attachments?: ChatAttachment[]
}

export async function uploadAttachment(
  conversationId: string,
  file: File,
): Promise<ChatAttachment> {
  const form = new FormData()
  form.append('file', file)
  // No explicit Content-Type: the browser sets the multipart boundary.
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}/attachments`,
    { method: 'POST', body: form },
  )
  if (!response.ok) {
    let detail = 'Failed to upload file'
    try {
      const data = (await response.json()) as { detail?: string }
      if (data.detail) {
        detail = data.detail
      }
    } catch {
      // keep default
    }
    throw new Error(detail)
  }
  return response.json()
}

export async function deleteAttachment(
  conversationId: string,
  attachmentId: string,
): Promise<void> {
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}/attachments/${attachmentId}`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    throw new Error('Failed to remove file')
  }
}

export type Conversation = {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

// The sidebar list is read straight from Supabase (RLS scopes it to the user).
export async function listConversations(): Promise<Conversation[]> {
  const { data, error } = await supabase
    .from('conversations')
    .select('id, title, created_at, updated_at')
    .order('updated_at', { ascending: false })

  if (error) {
    throw error
  }

  return data ?? []
}

export async function createConversation(): Promise<{ id: string; title: string }> {
  const response = await apiFetch('/api/v1/chat/conversations', {
    method: 'POST',
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    throw new Error('Failed to create conversation')
  }
  return response.json()
}

export async function loadMessages(conversationId: string): Promise<ChatMessage[]> {
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}/messages`,
  )
  if (!response.ok) {
    throw new Error('Failed to load messages')
  }
  const data = (await response.json()) as { messages?: ChatMessage[] }
  return data.messages ?? []
}

export async function renameConversation(
  conversationId: string,
  title: string,
): Promise<{ id: string; title: string }> {
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    },
  )
  if (!response.ok) {
    throw new Error('Failed to rename conversation')
  }
  return response.json()
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    throw new Error('Failed to delete conversation')
  }
}

export type StreamHandlers = {
  onDelta: (text: string) => void
  onDone: (info: { title?: string }) => void
  onError: (message: string) => void
}

// The client's local clock, so the assistant can resolve relative dates like
// "today" / "yesterday" using the user's timezone rather than the server's.
function clientNow(): { client_date: string; client_time: string; client_timezone?: string } {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  const client_date = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
  const client_time = `${pad(now.getHours())}:${pad(now.getMinutes())}`
  let client_timezone: string | undefined
  try {
    client_timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    client_timezone = undefined
  }
  return { client_date, client_time, client_timezone }
}

// Cached so we only prompt for the geolocation permission and reverse-geocode
// once per session. The browser itself only prompts once per site.
let cachedLocation: string | null = null

// Turn coordinates into a readable place (city/region/country) via a keyless
// client-side reverse-geocoding endpoint. Returns null on any failure.
async function reverseGeocode(latitude: number, longitude: number): Promise<string | null> {
  try {
    const response = await fetch(
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`,
    )
    if (!response.ok) {
      return null
    }
    const data = (await response.json()) as {
      locality?: string
      city?: string
      principalSubdivision?: string
      countryName?: string
    }
    const parts = [data.locality, data.city, data.principalSubdivision, data.countryName]
      .map((part) => (typeof part === 'string' ? part.trim() : ''))
      .filter(Boolean)
    const unique = parts.filter((part, index) => parts.indexOf(part) === index)
    return unique.length > 0 ? unique.join(', ') : null
  } catch {
    return null
  }
}

// Resolves the user's approximate location as a readable place string, or null
// if unavailable/denied. Never rejects, so a missing location just omits the
// field from the request.
async function clientLocation(): Promise<{ client_location: string } | null> {
  if (cachedLocation) {
    return { client_location: cachedLocation }
  }
  if (typeof navigator === 'undefined' || !('geolocation' in navigator)) {
    return null
  }
  const coords = await new Promise<{ latitude: number; longitude: number } | null>(
    (resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }),
        () => resolve(null),
        { timeout: 5000, maximumAge: 600000 },
      )
    },
  )
  if (!coords) {
    return null
  }
  const label = await reverseGeocode(coords.latitude, coords.longitude)
  if (!label) {
    return null
  }
  cachedLocation = label
  return { client_location: label }
}

// Sends a message and consumes the SSE stream. We use fetch (not EventSource)
// because EventSource can't attach the Authorization header.
export async function streamMessage(
  conversationId: string,
  text: string,
  handlers: StreamHandlers,
  options: { model?: string; attachmentIds?: string[] } = {},
): Promise<void> {
  const location = await clientLocation()
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({
        text,
        ...(options.model ? { model: options.model } : {}),
        ...(options.attachmentIds && options.attachmentIds.length > 0
          ? { attachment_ids: options.attachmentIds }
          : {}),
        ...clientNow(),
        ...(location ?? {}),
      }),
      headers: { Accept: 'text/event-stream' },
    },
  )

  if (!response.ok || !response.body) {
    handlers.onError('Failed to send message')
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex: number
    while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)

      const dataLine = frame
        .split('\n')
        .find((line) => line.startsWith('data:'))
      if (!dataLine) {
        continue
      }

      const json = dataLine.slice(5).trim()
      if (!json) {
        continue
      }

      let payload: { delta?: string; done?: boolean; title?: string; error?: string }
      try {
        payload = JSON.parse(json)
      } catch {
        continue
      }

      if (payload.error) {
        handlers.onError(payload.error)
      } else if (payload.delta) {
        handlers.onDelta(payload.delta)
      } else if (payload.done) {
        handlers.onDone({ title: payload.title })
      }
    }
  }
}
