import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type PanelMode = 'collapsed' | 'half' | 'full'

const MODE_STORAGE_KEY = 'chatPanelMode'
const BODY_CLASS: Record<PanelMode, string> = {
  collapsed: 'chat-collapsed',
  half: 'chat-half',
  full: 'chat-full',
}

function readInitialMode(): PanelMode {
  const stored = localStorage.getItem(MODE_STORAGE_KEY)
  if (stored === 'collapsed' || stored === 'half' || stored === 'full') {
    return stored
  }
  if (window.matchMedia('(max-width: 768px)').matches) {
    return 'collapsed'
  }
  return 'half'
}

type ChatUIContextValue = {
  mode: PanelMode
  setMode: (mode: PanelMode) => void
}

const ChatUIContext = createContext<ChatUIContextValue | null>(null)

export function ChatUIProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<PanelMode>(readInitialMode)

  useEffect(() => {
    localStorage.setItem(MODE_STORAGE_KEY, mode)
    document.body.classList.add(BODY_CLASS[mode])
    return () => document.body.classList.remove(BODY_CLASS[mode])
  }, [mode])

  return <ChatUIContext.Provider value={{ mode, setMode }}>{children}</ChatUIContext.Provider>
}

export function useChatUI(): ChatUIContextValue {
  const value = useContext(ChatUIContext)
  if (!value) {
    throw new Error('useChatUI must be used within a ChatUIProvider')
  }
  return value
}
