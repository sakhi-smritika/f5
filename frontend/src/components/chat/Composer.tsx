import { useState } from 'react'

type ComposerProps = {
  disabled: boolean
  onSend: (text: string) => void
}

export function Composer({ disabled, onSend }: ComposerProps) {
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
      <button
        type="button"
        className="chat-send"
        disabled={disabled || !text.trim()}
        onClick={submit}
      >
        Send
      </button>
    </div>
  )
}
