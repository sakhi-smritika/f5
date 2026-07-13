import { useState } from 'react'
import type { ChatModel } from '../../lib/models'
import { ModelSelector } from './ModelSelector'

type ComposerProps = {
  disabled: boolean
  models: ChatModel[]
  selectedModel: string
  onModelChange: (modelId: string) => void
  onSend: (text: string) => void
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

export function Composer({
  disabled,
  models,
  selectedModel,
  onModelChange,
  onSend,
}: ComposerProps) {
  const [text, setText] = useState('')

  const submit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) {
      return
    }
    onSend(trimmed)
    setText('')
  }

  return (
    <div className="chat-composer">
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
          disabled={disabled || !text.trim()}
          onClick={submit}
          aria-label="Send message"
          title="Send"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  )
}
