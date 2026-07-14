import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { FileText } from 'lucide-react'
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

export function MessageList({ messages, streaming, error }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  return (
    <div className="chat-messages">
      {messages.length === 0 && !streaming ? (
        <p className="chat-empty-hint">Ask me anything to get started.</p>
      ) : null}

      {messages.map((message, index) => (
        <div
          key={index}
          className={
            message.role === 'user'
              ? 'chat-message user'
              : 'chat-message assistant'
          }
        >
          {message.role === 'assistant' ? (
            <div className="chat-markdown">
              <ReactMarkdown>{message.text}</ReactMarkdown>
              {streaming && index === messages.length - 1 ? (
                <span className="chat-cursor" />
              ) : null}
            </div>
          ) : (
            <>
              {message.attachments && message.attachments.length > 0 ? (
                <div className="chat-message-attachments">
                  {message.attachments.map((attachment) => (
                    <AttachmentView key={attachment.id} attachment={attachment} />
                  ))}
                </div>
              ) : null}
              {message.text ? (
                <div className="chat-message-text">{message.text}</div>
              ) : null}
            </>
          )}
        </div>
      ))}

      {error ? <p className="chat-error">{error}</p> : null}

      <div ref={bottomRef} />
    </div>
  )
}
