import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from '../../lib/chat'

type MessageListProps = {
  messages: ChatMessage[]
  streaming: boolean
  error: string | null
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
            <div className="chat-message-text">{message.text}</div>
          )}
        </div>
      ))}

      {error ? <p className="chat-error">{error}</p> : null}

      <div ref={bottomRef} />
    </div>
  )
}
