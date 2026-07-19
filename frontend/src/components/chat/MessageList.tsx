import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Check, Copy, FileText } from 'lucide-react'
import type { ChatAttachment, ChatMessage } from '../../lib/chat'

type MessageListProps = {
  messages: ChatMessage[]
  streaming: boolean
  error: string | null
}

function AttachmentView({ attachment }: { attachment: ChatAttachment }) {
  const isImage = attachment.mime_type.startsWith('image/')
  if (isImage && attachment.url) {
    return (
      <a
        href={attachment.url}
        target="_blank"
        rel="noreferrer"
        className="chat-message-image"
      >
        <img src={attachment.url} alt={attachment.filename} />
      </a>
    )
  }
  const content = (
    <>
      <FileText size={16} />
      <span className="chat-file-card-name">{attachment.filename}</span>
    </>
  )
  return attachment.url ? (
    <a
      href={attachment.url}
      target="_blank"
      rel="noreferrer"
      className="chat-file-card"
    >
      {content}
    </a>
  ) : (
    <div className="chat-file-card">{content}</div>
  )
}

function CopyButton({
  text,
  onCopied,
}: {
  text: string
  onCopied: () => void
}) {
  const [copied, setCopied] = useState(false)
  const timerRef = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current)
      }
    },
    [],
  )

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      return
    }
    setCopied(true)
    onCopied()
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
    }
    timerRef.current = window.setTimeout(() => setCopied(false), 1000)
  }

  return (
    <button
      type="button"
      className="chat-copy-button"
      onClick={handleCopy}
      title="Copy message"
      aria-label="Copy message"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  )
}

export function MessageList({ messages, streaming, error }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const [showToast, setShowToast] = useState(false)
  const toastTimerRef = useRef<number | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  useEffect(
    () => () => {
      if (toastTimerRef.current) {
        window.clearTimeout(toastTimerRef.current)
      }
    },
    [],
  )

  const handleCopied = () => {
    setShowToast(true)
    if (toastTimerRef.current) {
      window.clearTimeout(toastTimerRef.current)
    }
    toastTimerRef.current = window.setTimeout(() => setShowToast(false), 1000)
  }

  return (
    <div className="chat-messages-wrap">
      {showToast ? (
        <div className="chat-toast" role="status" aria-live="polite">
          Copied!
        </div>
      ) : null}

      <div className="chat-messages">
        {messages.length === 0 && !streaming ? (
          <p className="chat-empty-hint">Ask me anything to get started.</p>
        ) : null}

        {messages.map((message, index) => {
          const isLast = index === messages.length - 1
          const canCopy = message.text.trim().length > 0

          return (
            <div
              key={index}
              className={
                message.role === 'user'
                  ? 'chat-message-row user'
                  : 'chat-message-row assistant'
              }
            >
              {canCopy ? (
                <CopyButton text={message.text} onCopied={handleCopied} />
              ) : null}

              <div
                className={
                  message.role === 'user'
                    ? 'chat-message user'
                    : 'chat-message assistant'
                }
              >
                {message.role === 'assistant' ? (
                  <div className="chat-markdown">
                    <ReactMarkdown>{message.text}</ReactMarkdown>
                    {streaming && isLast ? (
                      <span className="chat-cursor" />
                    ) : null}
                  </div>
                ) : (
                  <>
                    {message.attachments && message.attachments.length > 0 ? (
                      <div className="chat-message-attachments">
                        {message.attachments.map((attachment) => (
                          <AttachmentView
                            key={attachment.id}
                            attachment={attachment}
                          />
                        ))}
                      </div>
                    ) : null}
                    {message.text ? (
                      <div className="chat-message-text">{message.text}</div>
                    ) : null}
                  </>
                )}
              </div>
            </div>
          )
        })}

        {error ? <p className="chat-error">{error}</p> : null}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
