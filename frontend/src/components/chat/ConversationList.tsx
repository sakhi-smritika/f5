import { useEffect, useRef, useState } from 'react'
import type { ChatFolder, Conversation } from '../../lib/chat'

type ConversationListProps = {
  folders: ChatFolder[]
  conversations: Conversation[]
  activeId: string | null
  expandedFolderIds: Set<string>
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onRename: (id: string, title: string) => void
  onCreateFolder: (name: string) => void
  onRenameFolder: (id: string, name: string) => void
  onDeleteFolder: (id: string) => void
  onToggleFolder: (id: string) => void
  onMoveToFolder: (conversationId: string, folderId: string | null) => void
}

function PlusIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  )
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

function FolderIcon() {
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
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
    </svg>
  )
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={expanded ? 'chat-folder-chevron expanded' : 'chat-folder-chevron'}
    >
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}

function MoveIcon() {
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
      <path d="M3 7h18" />
      <path d="M3 12h18" />
      <path d="M3 17h18" />
    </svg>
  )
}

type ConversationItemProps = {
  conversation: Conversation
  activeId: string | null
  folders: ChatFolder[]
  editingId: string | null
  draftTitle: string
  moveMenuId: string | null
  inputRef: React.RefObject<HTMLInputElement | null>
  onSelect: (id: string) => void
  onStartEditing: (conversation: Conversation) => void
  onDraftChange: (value: string) => void
  onCommitEditing: () => void
  onCancelEditing: () => void
  onDeleteRequest: (id: string) => void
  onMoveMenuToggle: (id: string | null) => void
  onMoveToFolder: (conversationId: string, folderId: string | null) => void
  nested?: boolean
}

function ConversationItem({
  conversation,
  activeId,
  folders,
  editingId,
  draftTitle,
  moveMenuId,
  inputRef,
  onSelect,
  onStartEditing,
  onDraftChange,
  onCommitEditing,
  onCancelEditing,
  onDeleteRequest,
  onMoveMenuToggle,
  onMoveToFolder,
  nested = false,
}: ConversationItemProps) {
  const isActive = conversation.id === activeId
  const isEditing = conversation.id === editingId
  const showMoveMenu = moveMenuId === conversation.id

  return (
    <div
      className={
        nested
          ? isActive
            ? 'chat-conversation-item nested active'
            : 'chat-conversation-item nested'
          : isActive
            ? 'chat-conversation-item active'
            : 'chat-conversation-item'
      }
    >
      {isEditing ? (
        <input
          ref={inputRef}
          className="chat-conversation-edit"
          value={draftTitle}
          onChange={(event) => onDraftChange(event.target.value)}
          onBlur={onCommitEditing}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              onCommitEditing()
            } else if (event.key === 'Escape') {
              event.preventDefault()
              onCancelEditing()
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
            <div className="chat-move-menu-wrap">
              <button
                type="button"
                className="chat-conversation-action"
                aria-label="Move to folder"
                title="Move to folder"
                onClick={() =>
                  onMoveMenuToggle(showMoveMenu ? null : conversation.id)
                }
              >
                <MoveIcon />
              </button>
              {showMoveMenu ? (
                <div className="chat-move-menu" role="menu">
                  {conversation.folder_id ? (
                    <button
                      type="button"
                      className="chat-move-menu-item"
                      role="menuitem"
                      onClick={() => {
                        onMoveToFolder(conversation.id, null)
                        onMoveMenuToggle(null)
                      }}
                    >
                      Remove from folder
                    </button>
                  ) : null}
                  {folders.map((folder) => (
                    <button
                      key={folder.id}
                      type="button"
                      className={
                        folder.id === conversation.folder_id
                          ? 'chat-move-menu-item selected'
                          : 'chat-move-menu-item'
                      }
                      role="menuitem"
                      disabled={folder.id === conversation.folder_id}
                      onClick={() => {
                        onMoveToFolder(conversation.id, folder.id)
                        onMoveMenuToggle(null)
                      }}
                    >
                      {folder.name}
                    </button>
                  ))}
                  {folders.length === 0 && !conversation.folder_id ? (
                    <span className="chat-move-menu-empty">No folders yet</span>
                  ) : null}
                </div>
              ) : null}
            </div>
            <button
              type="button"
              className="chat-conversation-action"
              aria-label="Rename conversation"
              title="Rename"
              onClick={() => onStartEditing(conversation)}
            >
              <PencilIcon />
            </button>
            <button
              type="button"
              className="chat-conversation-action chat-conversation-action-danger"
              aria-label="Delete conversation"
              title="Delete"
              onClick={() => onDeleteRequest(conversation.id)}
            >
              <TrashIcon />
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export function ConversationList({
  folders,
  conversations,
  activeId,
  expandedFolderIds,
  onSelect,
  onNew,
  onDelete,
  onRename,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onToggleFolder,
  onMoveToFolder,
}: ConversationListProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftFolderName, setDraftFolderName] = useState('')
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const [pendingDeleteFolderId, setPendingDeleteFolderId] = useState<string | null>(null)
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [moveMenuId, setMoveMenuId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const folderInputRef = useRef<HTMLInputElement | null>(null)
  const newFolderInputRef = useRef<HTMLInputElement | null>(null)

  const pendingDeleteConversation =
    conversations.find((conversation) => conversation.id === pendingDeleteId) ?? null
  const pendingDeleteFolder =
    folders.find((folder) => folder.id === pendingDeleteFolderId) ?? null
  const unfolderedConversations = conversations.filter(
    (conversation) => !conversation.folder_id,
  )

  const conversationsByFolder = (folderId: string) =>
    conversations
      .filter((conversation) => conversation.folder_id === folderId)
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      )

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editingId])

  useEffect(() => {
    if (editingFolderId && folderInputRef.current) {
      folderInputRef.current.focus()
      folderInputRef.current.select()
    }
  }, [editingFolderId])

  useEffect(() => {
    if (creatingFolder && newFolderInputRef.current) {
      newFolderInputRef.current.focus()
    }
  }, [creatingFolder])

  const startEditing = (conversation: Conversation) => {
    setEditingId(conversation.id)
    setDraftTitle(conversation.title || '')
    setMoveMenuId(null)
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

  const startEditingFolder = (folder: ChatFolder) => {
    setEditingFolderId(folder.id)
    setDraftFolderName(folder.name)
  }

  const commitFolderEditing = () => {
    if (editingFolderId) {
      const trimmed = draftFolderName.trim()
      if (trimmed) {
        onRenameFolder(editingFolderId, trimmed)
      }
    }
    setEditingFolderId(null)
    setDraftFolderName('')
  }

  const cancelFolderEditing = () => {
    setEditingFolderId(null)
    setDraftFolderName('')
  }

  const commitNewFolder = () => {
    const trimmed = newFolderName.trim()
    if (trimmed) {
      onCreateFolder(trimmed)
    }
    setCreatingFolder(false)
    setNewFolderName('')
  }

  const cancelNewFolder = () => {
    setCreatingFolder(false)
    setNewFolderName('')
  }

  const confirmDelete = () => {
    if (pendingDeleteId) {
      onDelete(pendingDeleteId)
    }
    setPendingDeleteId(null)
  }

  const confirmDeleteFolder = () => {
    if (pendingDeleteFolderId) {
      onDeleteFolder(pendingDeleteFolderId)
    }
    setPendingDeleteFolderId(null)
  }

  const conversationItemProps = {
    activeId,
    folders,
    editingId,
    draftTitle,
    moveMenuId,
    inputRef,
    onSelect,
    onStartEditing: startEditing,
    onDraftChange: setDraftTitle,
    onCommitEditing: commitEditing,
    onCancelEditing: cancelEditing,
    onDeleteRequest: setPendingDeleteId,
    onMoveMenuToggle: setMoveMenuId,
    onMoveToFolder,
  }

  return (
    <div className="chat-conversations">
      <button type="button" className="chat-new" onClick={onNew}>
        + New chat
      </button>

      <div className="chat-conversation-items">
        <div className="chat-sidebar-section">
          <div className="chat-sidebar-section-header">
            <button
              type="button"
              className="chat-section-add"
              aria-label="New folder"
              title="New folder"
              onClick={() => setCreatingFolder(true)}
            >
              <PlusIcon />
            </button>
            <span>Folders</span>
          </div>

          {creatingFolder ? (
            <div className="chat-new-folder-form">
              <input
                ref={newFolderInputRef}
                className="chat-folder-edit"
                placeholder="Folder name"
                value={newFolderName}
                onChange={(event) => setNewFolderName(event.target.value)}
                onBlur={commitNewFolder}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault()
                    commitNewFolder()
                  } else if (event.key === 'Escape') {
                    event.preventDefault()
                    cancelNewFolder()
                  }
                }}
              />
            </div>
          ) : null}

          {folders.map((folder) => {
            const expanded = expandedFolderIds.has(folder.id)
            const folderConversations = conversationsByFolder(folder.id)
            const isEditingFolder = editingFolderId === folder.id

            return (
              <div key={folder.id} className="chat-folder-group">
                <div className="chat-folder-row">
                  {isEditingFolder ? (
                    <input
                      ref={folderInputRef}
                      className="chat-folder-edit"
                      value={draftFolderName}
                      onChange={(event) => setDraftFolderName(event.target.value)}
                      onBlur={commitFolderEditing}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault()
                          commitFolderEditing()
                        } else if (event.key === 'Escape') {
                          event.preventDefault()
                          cancelFolderEditing()
                        }
                      }}
                    />
                  ) : (
                    <>
                      <button
                        type="button"
                        className="chat-folder-toggle"
                        onClick={() => onToggleFolder(folder.id)}
                        aria-expanded={expanded}
                      >
                        <ChevronIcon expanded={expanded} />
                        <FolderIcon />
                        <span className="chat-folder-name">{folder.name}</span>
                      </button>
                      <div className="chat-folder-actions">
                        <button
                          type="button"
                          className="chat-conversation-action"
                          aria-label="Rename folder"
                          title="Rename"
                          onClick={() => startEditingFolder(folder)}
                        >
                          <PencilIcon />
                        </button>
                        <button
                          type="button"
                          className="chat-conversation-action chat-conversation-action-danger"
                          aria-label="Delete folder"
                          title="Delete"
                          onClick={() => setPendingDeleteFolderId(folder.id)}
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </>
                  )}
                </div>

                {expanded ? (
                  <div className="chat-folder-children">
                    {folderConversations.length === 0 ? (
                      <p className="chat-folder-empty">No chats in this folder.</p>
                    ) : (
                      folderConversations.map((conversation) => (
                        <ConversationItem
                          key={conversation.id}
                          conversation={conversation}
                          nested
                          {...conversationItemProps}
                        />
                      ))
                    )}
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>

        <div className="chat-sidebar-section">
          <div className="chat-sidebar-section-header">Chats</div>

          {unfolderedConversations.length === 0 ? (
            <p className="chat-section-empty">No chats yet.</p>
          ) : (
            unfolderedConversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                {...conversationItemProps}
              />
            ))
          )}
        </div>
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

      {pendingDeleteFolder ? (
        <div
          className="chat-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-folder-delete-title"
          onClick={() => setPendingDeleteFolderId(null)}
        >
          <div className="chat-modal" onClick={(event) => event.stopPropagation()}>
            <h2 id="chat-folder-delete-title" className="chat-modal-title">
              Delete folder?
            </h2>
            <p className="chat-modal-text">
              This will permanently delete{' '}
              <strong>{pendingDeleteFolder.name}</strong> and all conversations inside
              it. This action cannot be undone.
            </p>
            <div className="chat-modal-actions">
              <button
                type="button"
                className="chat-modal-button"
                onClick={() => setPendingDeleteFolderId(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="chat-modal-button chat-modal-button-danger"
                onClick={confirmDeleteFolder}
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
