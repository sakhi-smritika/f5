import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy, FileText, Quote } from 'lucide-react'
import type { ChatAttachment, ChatMessage } from '../../lib/chat'

type PinnedKbit = {
  title: string
  content: string
}

type MessageListProps = {
  messages: ChatMessage[]
  streaming: boolean
  error: string | null
  onQuote?: (text: string) => void
  // When set, the conversation is a knowledge-bit discussion: the bit is pinned
  // at the top of the thread so it reads as the subject of the discussion.
  pinnedKbit?: PinnedKbit | null
}

type QuoteButtonState = {
  top: number
  left: number
  text: string
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

export function MessageList({
  messages,
  streaming,
  error,
  onQuote,
  pinnedKbit,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const [showToast, setShowToast] = useState(false)
  const [quoteButton, setQuoteButton] = useState<QuoteButtonState | null>(null)
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

  useEffect(() => {
    const evaluateSelection = () => {
      const selection = window.getSelection()
      const wrap = wrapRef.current
      if (!selection || selection.isCollapsed || selection.rangeCount === 0 || !wrap) {
        setQuoteButton(null)
        return
      }
      const text = selection.toString().trim()
      if (!text) {
        setQuoteButton(null)
        return
      }
      const range = selection.getRangeAt(0)
      const node = range.commonAncestorContainer
      const element =
        node.nodeType === Node.TEXT_NODE ? node.parentElement : (node as Element | null)
      const withinAssistant = element?.closest('.chat-message.assistant')
      if (!withinAssistant) {
        setQuoteButton(null)
        return
      }
      const rect = range.getBoundingClientRect()
      const wrapRect = wrap.getBoundingClientRect()
      setQuoteButton({
        top: rect.top - wrapRect.top - 8,
        left: Math.min(
          Math.max(rect.left - wrapRect.left + rect.width / 2, 28),
          wrapRect.width - 28,
        ),
        text,
      })
    }

    const handleMouseUp = () => window.setTimeout(evaluateSelection, 0)
    document.addEventListener('mouseup', handleMouseUp)
    return () => document.removeEventListener('mouseup', handleMouseUp)
  }, [])

  useEffect(() => {
    const scroller = scrollRef.current
    if (!scroller) {
      return
    }
    const hide = () => setQuoteButton(null)
    scroller.addEventListener('scroll', hide)
    return () => scroller.removeEventListener('scroll', hide)
  }, [])

  const handleQuote = () => {
    if (quoteButton && onQuote) {
      onQuote(quoteButton.text)
    }
    window.getSelection()?.removeAllRanges()
    setQuoteButton(null)
  }

  const handleCopied = () => {
    setShowToast(true)
    if (toastTimerRef.current) {
      window.clearTimeout(toastTimerRef.current)
    }
    toastTimerRef.current = window.setTimeout(() => setShowToast(false), 1000)
  }

  return (
    <div className="chat-messages-wrap" ref={wrapRef}>
      {showToast ? (
        <div className="chat-toast" role="status" aria-live="polite">
          Copied!
        </div>
      ) : null}

      {quoteButton ? (
        <button
          type="button"
          className="chat-quote-button"
          style={{ top: quoteButton.top, left: quoteButton.left }}
          onMouseDown={(event) => event.preventDefault()}
          onClick={handleQuote}
          title="Quote in reply"
          aria-label="Quote selection in reply"
        >
          <Quote size={15} />
        </button>
      ) : null}

      <div className="chat-messages" ref={scrollRef}>
        {pinnedKbit ? (
          <div className="chat-pinned-kbit">
            <span className="chat-pinned-kbit-label">Knowledge Bit</span>
            <h3 className="chat-pinned-kbit-title">{pinnedKbit.title}</h3>
            <p className="chat-pinned-kbit-content">{pinnedKbit.content}</p>
          </div>
        ) : null}

        {messages.length === 0 && !streaming ? (
          <p className="chat-empty-hint">
            {pinnedKbit
              ? 'Add a comment to start discussing this with Smritika.'
              : 'Ask me anything to get started.'}
          </p>
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
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: ({ node, ...props }) => (
                          <a {...props} target="_blank" rel="noreferrer noopener" />
                        ),
                      }}
                    >
                      {message.text}
                    </ReactMarkdown>
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
