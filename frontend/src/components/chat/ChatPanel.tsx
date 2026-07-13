import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Maximize2, Minimize2, PanelRightClose, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import {
  createConversation,
  deleteConversation,
  listConversations,
  loadMessages,
  renameConversation,
  streamMessage,
  type ChatMessage,
  type Conversation,
} from '../../lib/chat'
import { Composer } from './Composer'
import { ConversationList } from './ConversationList'
import { MessageList } from './MessageList'
import { useChatUI } from './ChatUIContext'
import './ChatPanel.css'

function moveToTop(conversations: Conversation[], id: string): Conversation[] {
  const target = conversations.find((conversation) => conversation.id === id)
  if (!target) {
    return conversations
  }
  return [target, ...conversations.filter((conversation) => conversation.id !== id)]
}

function MenuIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 6h18" />
      <path d="M3 12h18" />
      <path d="M3 18h18" />
    </svg>
  )
}

export function ChatPanel() {
  const { user } = useAuth()
  const { mode, setMode } = useChatUI()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    if (!user?.id) {
      return
    }
    let cancelled = false
    listConversations()
      .then((rows) => {
        if (!cancelled) {
          setConversations(rows)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setConversations([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [user?.id])

  const closeSidebarOnMobile = useCallback(() => {
    if (window.matchMedia('(max-width: 768px)').matches) {
      setSidebarOpen(false)
    }
  }, [])

  const handleNew = useCallback(() => {
    setActiveId(null)
    setMessages([])
    setError(null)
    closeSidebarOnMobile()
  }, [closeSidebarOnMobile])

  const handleSelect = useCallback(
    async (id: string) => {
      setActiveId(id)
      setMessages([])
      setError(null)
      closeSidebarOnMobile()
      try {
        const loaded = await loadMessages(id)
        setMessages(loaded)
      } catch {
        setError('Failed to load messages')
      }
    },
    [closeSidebarOnMobile],
  )

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id)
      } catch {
        setError('Failed to delete conversation')
        return
      }
      setConversations((prev) => prev.filter((conversation) => conversation.id !== id))
      setActiveId((current) => {
        if (current === id) {
          setMessages([])
          return null
        }
        return current
      })
    },
    [],
  )

  const handleRename = useCallback(
    async (id: string, title: string) => {
      const trimmed = title.trim()
      if (!trimmed) {
        return
      }
      const previous = conversations
      setConversations((prev) =>
        prev.map((conversation) =>
          conversation.id === id ? { ...conversation, title: trimmed } : conversation,
        ),
      )
      try {
        await renameConversation(id, trimmed)
      } catch {
        setConversations(previous)
        setError('Failed to rename conversation')
      }
    },
    [conversations],
  )

  const handleSend = useCallback(
    async (text: string) => {
      if (streaming) {
        return
      }

      let conversationId = activeId
      if (!conversationId) {
        try {
          const created = await createConversation()
          conversationId = created.id
          const now = new Date().toISOString()
          setActiveId(created.id)
          setConversations((prev) => [
            { id: created.id, title: created.title, created_at: now, updated_at: now },
            ...prev,
          ])
        } catch {
          setError('Failed to start a conversation')
          return
        }
      }

      const targetId = conversationId
      setError(null)
      setMessages((prev) => [
        ...prev,
        { role: 'user', text },
        { role: 'assistant', text: '' },
      ])
      setStreaming(true)

      try {
        await streamMessage(targetId, text, {
          onDelta: (delta) =>
            setMessages((prev) => {
              const copy = prev.slice()
              const last = copy[copy.length - 1]
              copy[copy.length - 1] = { ...last, text: last.text + delta }
              return copy
            }),
          onError: () => setError('The assistant failed to respond.'),
          onDone: ({ title }) => {
            setConversations((prev) => {
              const updated = prev.map((conversation) =>
                conversation.id === targetId
                  ? {
                      ...conversation,
                      title: title ?? conversation.title,
                      updated_at: new Date().toISOString(),
                    }
                  : conversation,
              )
              return moveToTop(updated, targetId)
            })
          },
        })
      } finally {
        setStreaming(false)
      }
    },
    [activeId, streaming],
  )

  if (mode === 'collapsed') {
    return createPortal(
      <aside className="chat-panel chat-panel-rail">
        <button
          type="button"
          className="chat-rail-button"
          onClick={() => setMode('half')}
          title="Open Sakhi Smritika"
        >
          <span className="chat-rail-label">Sakhi Smritika</span>
        </button>
      </aside>,
      document.body,
    )
  }

  return createPortal(
    <aside className="chat-panel">
      <header className="chat-header">
        <div className="chat-header-left">
          <button
            type="button"
            className="chat-header-button chat-sidebar-toggle"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label={sidebarOpen ? 'Hide conversations' : 'Show conversations'}
            aria-pressed={sidebarOpen}
            title={sidebarOpen ? 'Hide conversations' : 'Show conversations'}
          >
            <MenuIcon />
          </button>
          <span className="chat-header-title">Sakhi Smritika</span>
        </div>
        <div className="chat-header-actions">
          <button
            type="button"
            className="chat-header-button chat-fullscreen-button"
            onClick={() => setMode(mode === 'full' ? 'half' : 'full')}
            aria-label={mode === 'full' ? 'Exit fullscreen' : 'Fullscreen'}
            title={mode === 'full' ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {mode === 'full' ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
          </button>
          <button
            type="button"
            className="chat-header-button chat-collapse-button"
            onClick={() => setMode('collapsed')}
            aria-label="Collapse"
            title="Collapse"
          >
            <span className="chat-collapse-icon">
              <PanelRightClose size={20} />
            </span>
            <span className="chat-close-icon">
              <X size={20} />
            </span>
          </button>
        </div>
      </header>

      <div className={sidebarOpen ? 'chat-body sidebar-open' : 'chat-body sidebar-closed'}>
        <ConversationList
          conversations={conversations}
          activeId={activeId}
          onSelect={handleSelect}
          onNew={handleNew}
          onDelete={handleDelete}
          onRename={handleRename}
        />
        <button
          type="button"
          className="chat-sidebar-backdrop"
          aria-label="Close conversations"
          onClick={() => setSidebarOpen(false)}
        />
        <div className="chat-main">
          <MessageList messages={messages} streaming={streaming} error={error} />
          <Composer disabled={streaming} onSend={handleSend} />
        </div>
      </div>
    </aside>,
    document.body,
  )
}
