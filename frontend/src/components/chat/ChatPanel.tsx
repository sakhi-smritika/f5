import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Maximize2, Minimize2, PanelRightClose, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import {
  createConversation,
  createFolder,
  deleteConversation,
  deleteFolder,
  listConversations,
  listFolders,
  loadMessages,
  moveConversationToFolder,
  renameConversation,
  renameFolder,
  applyToolStep,
  streamMessage,
  type ChatAttachment,
  type ChatFolder,
  type ChatMessage,
  type Conversation,
} from '../../lib/chat'
import {
  getStoredChatModel,
  listChatModels,
  setStoredChatModel,
  type ChatModel,
} from '../../lib/models'
import { getKbitById } from '../../lib/kbits'
import { Composer } from './Composer'
import { ConversationList } from './ConversationList'
import { MessageList } from './MessageList'
import { AppLogo } from '../AppLogo'
import { APP_NAME } from '../../lib/brand'
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
  const [folders, setFolders] = useState<ChatFolder[]>([])
  const [expandedFolderIds, setExpandedFolderIds] = useState<Set<string>>(new Set())
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [models, setModels] = useState<ChatModel[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [quote, setQuote] = useState<string | null>(null)
  // The bit pinned at the top when the active conversation is a kbit discussion.
  const [activeKbit, setActiveKbit] = useState<{ title: string; content: string } | null>(
    null,
  )

  useEffect(() => {
    if (!user?.id) {
      return
    }
    let cancelled = false
    Promise.all([listConversations(), listFolders()])
      .then(([conversationRows, folderRows]) => {
        if (!cancelled) {
          setConversations(conversationRows)
          setFolders(folderRows)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setConversations([])
          setFolders([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [user?.id])

  useEffect(() => {
    let cancelled = false
    listChatModels()
      .then(({ default: defaultModel, models: availableModels }) => {
        if (cancelled) {
          return
        }
        setModels(availableModels)
        const stored = getStoredChatModel()
        const initial =
          stored && availableModels.some((model) => model.id === stored)
            ? stored
            : defaultModel
        setSelectedModel(initial)
      })
      .catch(() => {
        if (!cancelled) {
          setModels([])
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleModelChange = useCallback((modelId: string) => {
    setSelectedModel(modelId)
    setStoredChatModel(modelId)
  }, [])

  const closeSidebarOnMobile = useCallback(() => {
    if (window.matchMedia('(max-width: 768px)').matches) {
      setSidebarOpen(false)
    }
  }, [])

  const handleNew = useCallback(() => {
    setActiveId(null)
    setMessages([])
    setError(null)
    setActiveKbit(null)
    closeSidebarOnMobile()
  }, [closeSidebarOnMobile])

  const handleSelect = useCallback(
    async (id: string) => {
      setActiveId(id)
      setMessages([])
      setError(null)
      setActiveKbit(null)
      closeSidebarOnMobile()

      const kbitId =
        conversations.find((conversation) => conversation.id === id)?.kbit_id ?? null
      if (kbitId) {
        getKbitById(kbitId)
          .then((bit) =>
            setActiveKbit(bit ? { title: bit.title, content: bit.content } : null),
          )
          .catch(() => setActiveKbit(null))
      }

      try {
        const loaded = await loadMessages(id)
        setMessages(loaded)
      } catch {
        setError('Failed to load messages')
      }
    },
    [closeSidebarOnMobile, conversations],
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

  const handleCreateFolder = useCallback(async (name: string) => {
    const trimmed = name.trim()
    if (!trimmed) {
      return
    }
    try {
      const folder = await createFolder(trimmed)
      setFolders((prev) =>
        [...prev, folder].sort((a, b) => a.name.localeCompare(b.name)),
      )
      setExpandedFolderIds((prev) => new Set(prev).add(folder.id))
    } catch {
      setError('Failed to create folder')
    }
  }, [])

  const handleRenameFolder = useCallback(
    async (id: string, name: string) => {
      const trimmed = name.trim()
      if (!trimmed) {
        return
      }
      const previous = folders
      setFolders((prev) =>
        prev
          .map((folder) => (folder.id === id ? { ...folder, name: trimmed } : folder))
          .sort((a, b) => a.name.localeCompare(b.name)),
      )
      try {
        await renameFolder(id, trimmed)
      } catch {
        setFolders(previous)
        setError('Failed to rename folder')
      }
    },
    [folders],
  )

  const handleDeleteFolder = useCallback(
    async (id: string) => {
      const removedConversations = conversations.filter(
        (conversation) => conversation.folder_id === id,
      )
      try {
        await deleteFolder(id)
      } catch {
        setError('Failed to delete folder')
        return
      }
      setFolders((prev) => prev.filter((folder) => folder.id !== id))
      setConversations((prev) =>
        prev.filter((conversation) => conversation.folder_id !== id),
      )
      setExpandedFolderIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      const removedIds = new Set(removedConversations.map((conversation) => conversation.id))
      setActiveId((current) => {
        if (current && removedIds.has(current)) {
          setMessages([])
          return null
        }
        return current
      })
    },
    [conversations],
  )

  const handleToggleFolder = useCallback((id: string) => {
    setExpandedFolderIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleMoveToFolder = useCallback(
    async (conversationId: string, folderId: string | null) => {
      const previous = conversations
      setConversations((prev) =>
        prev.map((conversation) =>
          conversation.id === conversationId
            ? { ...conversation, folder_id: folderId }
            : conversation,
        ),
      )
      if (folderId) {
        setExpandedFolderIds((prev) => new Set(prev).add(folderId))
      }
      try {
        await moveConversationToFolder(conversationId, folderId)
      } catch {
        setConversations(previous)
        setError('Failed to move conversation')
      }
    },
    [conversations],
  )

  const ensureConversation = useCallback(async (): Promise<string | null> => {
    if (activeId) {
      return activeId
    }
    try {
      const created = await createConversation()
      const now = new Date().toISOString()
      setActiveId(created.id)
      setConversations((prev) => [
        {
          id: created.id,
          title: created.title,
          folder_id: created.folder_id ?? null,
          created_at: now,
          updated_at: now,
        },
        ...prev,
      ])
      return created.id
    } catch {
      setError('Failed to start a conversation')
      return null
    }
  }, [activeId])

  const handleSend = useCallback(
    async ({
      text,
      attachments,
    }: {
      text: string
      attachments: ChatAttachment[]
    }) => {
      if (streaming) {
        return
      }

      const targetId = await ensureConversation()
      if (!targetId) {
        return
      }

      setError(null)
      setMessages((prev) => [
        ...prev,
        { role: 'user', text, attachments },
        { role: 'assistant', text: '' },
      ])
      setStreaming(true)

      try {
        await streamMessage(
          targetId,
          text,
          {
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
            onError: (message) =>
            setError(message || 'The assistant failed to respond.'),
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
          },
          {
            model: selectedModel || undefined,
            attachmentIds: attachments.map((attachment) => attachment.id),
          },
        )
      } finally {
        setStreaming(false)
      }
    },
    [ensureConversation, selectedModel, streaming],
  )

  if (mode === 'collapsed') {
    return createPortal(
      <aside className="chat-panel chat-panel-rail">
        <button
          type="button"
          className="chat-rail-button"
          onClick={() => setMode('half')}
          title={`Open ${APP_NAME}`}
        >
          <AppLogo size={28} className="chat-rail-logo" />
          <span className="chat-rail-label">{APP_NAME}</span>
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
          <span className="chat-header-brand">
            <AppLogo size={24} />
            <span className="chat-header-title">{APP_NAME}</span>
          </span>
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
          folders={folders}
          conversations={conversations}
          activeId={activeId}
          expandedFolderIds={expandedFolderIds}
          onSelect={handleSelect}
          onNew={handleNew}
          onDelete={handleDelete}
          onRename={handleRename}
          onCreateFolder={handleCreateFolder}
          onRenameFolder={handleRenameFolder}
          onDeleteFolder={handleDeleteFolder}
          onToggleFolder={handleToggleFolder}
          onMoveToFolder={handleMoveToFolder}
        />
        <button
          type="button"
          className="chat-sidebar-backdrop"
          aria-label="Close conversations"
          onClick={() => setSidebarOpen(false)}
        />
        <div className="chat-main">
          <MessageList
            messages={messages}
            streaming={streaming}
            error={error}
            onQuote={setQuote}
            pinnedKbit={activeKbit}
          />
          <Composer
            disabled={streaming}
            models={models}
            selectedModel={selectedModel}
            onModelChange={handleModelChange}
            onSend={handleSend}
            ensureConversation={ensureConversation}
            quote={quote}
            onClearQuote={() => setQuote(null)}
          />
        </div>
      </div>
    </aside>,
    document.body,
  )
}
