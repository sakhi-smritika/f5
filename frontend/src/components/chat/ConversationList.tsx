import { useEffect, useRef, useState } from 'react'
import type { Conversation } from '../../lib/chat'

type ConversationListProps = {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onRename: (id: string, title: string) => void
}

function PencilIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  )
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onRename,
}: ConversationListProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const pendingDeleteConversation =
    conversations.find((conversation) => conversation.id === pendingDeleteId) ?? null

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editingId])

  const startEditing = (conversation: Conversation) => {
    setEditingId(conversation.id)
    setDraftTitle(conversation.title || '')
  }

  const commitEditing = () => {
    if (editingId) {
      const trimmed = draftTitle.trim()
      if (trimmed) {
        onRename(editingId, trimmed)
      }
    }
    setEditingId(null)
    setDraftTitle('')
  }

  const cancelEditing = () => {
    setEditingId(null)
    setDraftTitle('')
  }

  const confirmDelete = () => {
    if (pendingDeleteId) {
      onDelete(pendingDeleteId)
    }
    setPendingDeleteId(null)
  }

  return (
    <div className="chat-conversations">
      <button type="button" className="chat-new" onClick={onNew}>
        + New chat
      </button>
      <div className="chat-conversation-items">
        {conversations.length === 0 ? (
          <p className="chat-empty-hint">No conversations yet.</p>
        ) : (
          conversations.map((conversation) => {
            const isActive = conversation.id === activeId
            const isEditing = conversation.id === editingId
            return (
              <div
                key={conversation.id}
                className={
                  isActive
                    ? 'chat-conversation-item active'
                    : 'chat-conversation-item'
                }
              >
                {isEditing ? (
                  <input
                    ref={inputRef}
                    className="chat-conversation-edit"
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                    onBlur={commitEditing}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        commitEditing()
                      } else if (event.key === 'Escape') {
                        event.preventDefault()
                        cancelEditing()
                      }
                    }}
                  />
                ) : (
                  <>
                    <button
                      type="button"
                      className="chat-conversation-select"
                      onClick={() => onSelect(conversation.id)}
                      title={conversation.title ?? 'Untitled'}
                    >
                      {conversation.title || 'Untitled'}
                    </button>
                    <div className="chat-conversation-actions">
                      <button
                        type="button"
                        className="chat-conversation-action"
                        aria-label="Rename conversation"
                        title="Rename"
                        onClick={() => startEditing(conversation)}
                      >
                        <PencilIcon />
                      </button>
                      <button
                        type="button"
                        className="chat-conversation-action chat-conversation-action-danger"
                        aria-label="Delete conversation"
                        title="Delete"
                        onClick={() => setPendingDeleteId(conversation.id)}
                      >
                        <TrashIcon />
                      </button>
                    </div>
                  </>
                )}
              </div>
            )
          })
        )}
      </div>

      {pendingDeleteConversation ? (
        <div
          className="chat-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-delete-title"
          onClick={() => setPendingDeleteId(null)}
        >
          <div className="chat-modal" onClick={(event) => event.stopPropagation()}>
            <h2 id="chat-delete-title" className="chat-modal-title">
              Delete conversation?
            </h2>
            <p className="chat-modal-text">
              This will permanently delete{' '}
              <strong>{pendingDeleteConversation.title || 'Untitled'}</strong> and its
              messages. This action cannot be undone.
            </p>
            <div className="chat-modal-actions">
              <button
                type="button"
                className="chat-modal-button"
                onClick={() => setPendingDeleteId(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="chat-modal-button chat-modal-button-danger"
                onClick={confirmDelete}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
