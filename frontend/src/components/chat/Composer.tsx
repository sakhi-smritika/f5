import { useRef, useState } from 'react'
import { CornerDownRight, Paperclip, X } from 'lucide-react'
import type { ChatModel } from '../../lib/models'
import {
  deleteAttachment,
  uploadAttachment,
  type ChatAttachment,
} from '../../lib/chat'
import { ModelSelector } from './ModelSelector'

type ComposerProps = {
  disabled: boolean
  models: ChatModel[]
  selectedModel: string
  onModelChange: (modelId: string) => void
  onSend: (payload: { text: string; attachments: ChatAttachment[] }) => void
  ensureConversation: () => Promise<string | null>
  quote?: string | null
  onClearQuote?: () => void
}

type PendingAttachment = {
  localId: string
  filename: string
  status: 'uploading' | 'ready' | 'error'
  attachment?: ChatAttachment
  error?: string
}

function SendIcon() {
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
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4Z" />
    </svg>
  )
}

let localIdCounter = 0
function nextLocalId(): string {
  localIdCounter += 1
  return `pending-${localIdCounter}`
}

export function Composer({
  disabled,
  models,
  selectedModel,
  onModelChange,
  onSend,
  ensureConversation,
  quote,
  onClearQuote,
}: ComposerProps) {
  const [text, setText] = useState('')
  const [pending, setPending] = useState<PendingAttachment[]>([])
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const conversationIdRef = useRef<string | null>(null)

  const uploading = pending.some((item) => item.status === 'uploading')
  const readyAttachments = pending
    .filter((item) => item.status === 'ready' && item.attachment)
    .map((item) => item.attachment as ChatAttachment)

  const handleFiles = async (selected: File[]) => {
    if (selected.length === 0) {
      return
    }
    const conversationId = await ensureConversation()
    if (!conversationId) {
      return
    }
    conversationIdRef.current = conversationId

    for (const file of selected) {
      const localId = nextLocalId()
      setPending((prev) => [
        ...prev,
        { localId, filename: file.name, status: 'uploading' },
      ])
      try {
        const attachment = await uploadAttachment(conversationId, file)
        setPending((prev) =>
          prev.map((item) =>
            item.localId === localId
              ? { ...item, status: 'ready', attachment }
              : item,
          ),
        )
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Upload failed'
        setPending((prev) =>
          prev.map((item) =>
            item.localId === localId
              ? { ...item, status: 'error', error: message }
              : item,
          ),
        )
      }
    }
  }

  const removePending = async (localId: string) => {
    const target = pending.find((item) => item.localId === localId)
    setPending((prev) => prev.filter((item) => item.localId !== localId))
    const conversationId = conversationIdRef.current
    if (target?.attachment && conversationId) {
      try {
        await deleteAttachment(conversationId, target.attachment.id)
      } catch {
        // Best-effort: orphaned uploads are cleaned up server-side later.
      }
    }
  }

  const submit = () => {
    const trimmed = text.trim()
    if (disabled || uploading) {
      return
    }
    if (!trimmed && readyAttachments.length === 0) {
      return
    }
    const quoted = quote
      ? `${quote
          .split('\n')
          .map((line) => `> ${line}`)
          .join('\n')}\n\n`
      : ''
    onSend({ text: quoted + trimmed, attachments: readyAttachments })
    setText('')
    setPending([])
    onClearQuote?.()
  }

  const canSend =
    !disabled && !uploading && (Boolean(text.trim()) || readyAttachments.length > 0)

  return (
    <div className="chat-composer-wrap">
      {quote ? (
        <div className="chat-quote-preview">
          <CornerDownRight size={16} className="chat-quote-preview-icon" />
          <span className="chat-quote-preview-text">{quote}</span>
          <button
            type="button"
            className="chat-quote-preview-remove"
            onClick={onClearQuote}
            aria-label="Remove quote"
          >
            <X size={14} />
          </button>
        </div>
      ) : null}

      {pending.length > 0 ? (
        <div className="chat-attachments">
          {pending.map((item) => (
            <div
              key={item.localId}
              className={`chat-attachment-chip ${item.status}`}
              title={item.error ?? item.filename}
            >
              <Paperclip size={14} />
              <span className="chat-attachment-name">{item.filename}</span>
              {item.status === 'uploading' ? (
                <span className="chat-attachment-status">…</span>
              ) : null}
              <button
                type="button"
                className="chat-attachment-remove"
                onClick={() => removePending(item.localId)}
                aria-label={`Remove ${item.filename}`}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : null}

      <div className="chat-composer">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="chat-file-input"
          onChange={(event) => {
            const files = Array.from(event.target.files ?? [])
            event.target.value = ''
            void handleFiles(files)
          }}
        />
        <button
          type="button"
          className="chat-attach-button"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          aria-label="Attach files"
          title="Attach files"
        >
          <Paperclip size={20} />
        </button>
        <textarea
          className="chat-composer-input"
          value={text}
          placeholder="Send a message..."
          rows={1}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit()
            }
          }}
        />
        <div className="chat-composer-actions">
          <ModelSelector
            models={models}
            value={selectedModel}
            disabled={disabled}
            onChange={onModelChange}
          />
          <button
            type="button"
            className="chat-send"
            disabled={!canSend}
            onClick={submit}
            aria-label="Send message"
            title="Send"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  )
}
