import { apiFetch } from './api'
import { supabase } from './supabase'

export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  role: ChatRole
  text: string
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

// Sends a message and consumes the SSE stream. We use fetch (not EventSource)
// because EventSource can't attach the Authorization header.
export async function streamMessage(
  conversationId: string,
  text: string,
  handlers: StreamHandlers,
): Promise<void> {
  const response = await apiFetch(
    `/api/v1/chat/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({ text }),
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
