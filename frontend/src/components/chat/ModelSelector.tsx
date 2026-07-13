import { useEffect, useRef, useState } from 'react'
import { Sparkles } from 'lucide-react'
import type { ChatModel } from '../../lib/models'

type ModelSelectorProps = {
  models: ChatModel[]
  value: string
  disabled?: boolean
  onChange: (modelId: string) => void
}

export function ModelSelector({
  models,
  value,
  disabled = false,
  onChange,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }
    const close = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  if (models.length <= 1) {
    return null
  }

  const current = models.find((model) => model.id === value)

  return (
    <div className="chat-model-picker" ref={rootRef}>
      <button
        type="button"
        className="chat-model-trigger"
        disabled={disabled}
        aria-label={`Model: ${current?.label ?? value}`}
        aria-expanded={open}
        aria-haspopup="listbox"
        title={`Model: ${current?.label ?? value}`}
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        <Sparkles size={18} />
      </button>
      {open ? (
        <div className="chat-model-menu" role="listbox" aria-label="Chat model">
          {models.map((model) => (
            <button
              key={model.id}
              type="button"
              role="option"
              aria-selected={model.id === value}
              className={
                model.id === value
                  ? 'chat-model-option chat-model-option-selected'
                  : 'chat-model-option'
              }
              onClick={() => {
                onChange(model.id)
                setOpen(false)
              }}
            >
              {model.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
