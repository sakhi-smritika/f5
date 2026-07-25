import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { SendHorizontal } from 'lucide-react'
import {
  applyToolStep,
  loadMessages,
  streamMessage,
  type ChatMessage,
} from '../../lib/chat'
import { ensureKbitDiscussion } from '../../lib/kbits'
import { MessageList } from '../chat/MessageList'
import './KbitComments.css'

type KbitCommentsProps = {
  kbitId: string
  // Fired once the discussion conversation exists, so the feed can show the
  // "being discussed" indicator without re-fetching.
  onStarted?: (conversationId: string) => void
}

export function KbitComments({ kbitId, onStarted }: KbitCommentsProps) {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) {
      return
    }
    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  }, [text])

  useEffect(() => {
    // `loading` starts true and the component remounts each time the section is
    // opened, so we avoid resetting state synchronously in the effect body and
    // only update it from the async callbacks below.
    let cancelled = false
    ensureKbitDiscussion(kbitId)
      .then(async (id) => {
        if (cancelled) {
          return
        }
        setConversationId(id)
        onStarted?.(id)
        try {
          const loaded = await loadMessages(id)
          if (!cancelled) {
            setMessages(loaded)
          }
        } catch {
          if (!cancelled) {
            setError('Failed to load comments')
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to open discussion')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [kbitId, onStarted])

  const submit = useCallback(async () => {
    const trimmed = text.trim()
    if (!trimmed || streaming || loading || !conversationId) {
      return
    }
    setText('')
    setError(null)
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: trimmed },
      { role: 'assistant', text: '' },
    ])
    setStreaming(true)
    try {
      await streamMessage(conversationId, trimmed, {
        onDelta: (delta) =>
          setMessages((prev) => {
            const copy = prev.slice()
            const last = copy[copy.length - 1]
            copy[copy.length - 1] = { ...last, text: last.text + delta }
            return copy
          }),
        onTool: (step) =>
          setMessages((prev) => {
            const copy = prev.slice()
            const last = copy[copy.length - 1]
            if (last?.role !== 'assistant') {
              return prev
            }
            copy[copy.length - 1] = {
              ...last,
              tool_steps: applyToolStep(last.tool_steps, step),
            }
            return copy
          }),
        onError: (message) => setError(message || 'Smritika failed to respond.'),
        onDone: () => {},
      })
    } finally {
      setStreaming(false)
    }
  }, [text, streaming, loading, conversationId])

  const canSend = Boolean(text.trim()) && !streaming && !loading

  return (
    <div className="kbit-comments">
      {loading ? (
        <p className="kbit-comments-status">Loading discussion…</p>
      ) : messages.length === 0 && !streaming ? (
        <p className="kbit-comments-empty">
          Start the discussion. Your first comment, together with this bit, begins a
          thread with Smritika.
        </p>
      ) : (
        <div className="kbit-comments-thread">
          <MessageList messages={messages} streaming={streaming} error={null} />
        </div>
      )}

      {error ? <p className="kbit-comments-error">{error}</p> : null}

      <div className="kbit-comments-composer">
        <textarea
          ref={textareaRef}
          className="kbit-comments-input"
          value={text}
          rows={1}
          placeholder="Add a comment…"
          disabled={streaming || loading}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              void submit()
            }
          }}
        />
        <button
          type="button"
          className="kbit-comments-send"
          disabled={!canSend}
          onClick={() => void submit()}
          aria-label="Send comment"
          title="Send"
        >
          <SendHorizontal size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
