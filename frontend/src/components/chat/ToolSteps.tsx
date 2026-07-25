import { useState } from 'react'
import { ChevronDown, ChevronRight, LoaderCircle, Wrench } from 'lucide-react'
import type { ToolStep } from '../../lib/chat'

function statusLabel(status: ToolStep['status']): string {
  if (status === 'running') {
    return 'running'
  }
  if (status === 'error') {
    return 'error'
  }
  return 'done'
}

function formatArgs(args: Record<string, unknown> | undefined): string {
  if (!args || Object.keys(args).length === 0) {
    return '{}'
  }
  try {
    return JSON.stringify(args, null, 2)
  } catch {
    return String(args)
  }
}

type ToolStepsProps = {
  steps: ToolStep[]
}

export function ToolSteps({ steps }: ToolStepsProps) {
  const [expanded, setExpanded] = useState(false)

  if (steps.length === 0) {
    return null
  }

  // Collapsed: show the in-flight tool, else the most recent one.
  const current =
    steps.find((step) => step.status === 'running') ?? steps[steps.length - 1]

  return (
    <div className="chat-tool-steps">
      <button
        type="button"
        className="chat-tool-steps-toggle"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {current.status === 'running' ? (
          <LoaderCircle size={14} className="chat-tool-spin" />
        ) : (
          <Wrench size={14} />
        )}
        <span className="chat-tool-steps-name">{current.name}</span>
        <span className={`chat-tool-steps-status ${current.status}`}>
          {statusLabel(current.status)}
        </span>
        {steps.length > 1 ? (
          <span className="chat-tool-steps-count">{steps.length} steps</span>
        ) : null}
      </button>

      {expanded ? (
        <ol className="chat-tool-steps-list">
          {steps.map((step) => (
            <li key={step.id} className={`chat-tool-step ${step.status}`}>
              <div className="chat-tool-step-header">
                <span className="chat-tool-step-name">{step.name}</span>
                <span className={`chat-tool-steps-status ${step.status}`}>
                  {statusLabel(step.status)}
                </span>
              </div>
              <pre className="chat-tool-step-args">{formatArgs(step.args)}</pre>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  )
}
