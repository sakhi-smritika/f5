import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  BookOpen,
  Brain,
  Icon,
  ListChecks,
  LogOut,
  MessageCircle,
  Puzzle,
  Settings,
  type LucideIcon,
} from 'lucide-react'
import { targetArrow } from '@lucide/lab'
import { useAuth } from '../context/AuthContext'
import { getProfile } from '../lib/profile'
import { ChatPanel } from './chat/ChatPanel'
import { ChatUIProvider, useChatUI } from './chat/ChatUIContext'
import './Layout.css'

const iconSize = 20

type NavItem = {
  label: string
  to: string
  Icon: LucideIcon
}

const introspectionItems: NavItem[] = [
  { label: 'Diary', to: '/introspection/diary', Icon: BookOpen },
  { label: 'Day Log', to: '/introspection/day-log', Icon: ListChecks },
]

export function Layout() {
  return (
    <ChatUIProvider>
      <LayoutInner />
    </ChatUIProvider>
  )
}

function LayoutInner() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const { setMode } = useChatUI()
  const [introspectionOpen, setIntrospectionOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [confirmSignOut, setConfirmSignOut] = useState(false)
  const [displayName, setDisplayName] = useState<string | null>(null)
  const introspectionRef = useRef<HTMLDivElement | null>(null)
  const settingsRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (introspectionRef.current && !introspectionRef.current.contains(event.target as Node)) {
        setIntrospectionOpen(false)
      }
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setSettingsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadProfile() {
      if (!user?.id) {
        setDisplayName(null)
        return
      }

      try {
        const profile = await getProfile(user.id)
        if (!cancelled) {
          setDisplayName(profile?.display_name ?? null)
        }
      } catch {
        if (!cancelled) {
          setDisplayName(null)
        }
      }
    }

    void loadProfile()

    return () => {
      cancelled = true
    }
  }, [user?.id])

  const accountLabel = displayName ?? user?.email ?? null

  return (
    <>
      <header className="layout-header">
        <nav className="pane-nav">
          <div className="pane-category" ref={introspectionRef}>
            <button
              type="button"
              className="icon-button"
              aria-expanded={introspectionOpen}
              aria-label="Introspection"
              title="Introspection"
              onClick={() => setIntrospectionOpen((open) => !open)}
            >
              <Brain size={iconSize} aria-hidden="true" />
            </button>
            {introspectionOpen ? (
              <div className="pane-menu">
                {introspectionItems.map(({ label, to, Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      isActive
                        ? 'icon-button pane-menu-icon active'
                        : 'icon-button pane-menu-icon'
                    }
                    aria-label={label}
                    title={label}
                    onClick={() => setIntrospectionOpen(false)}
                  >
                    <Icon size={iconSize} aria-hidden="true" />
                  </NavLink>
                ))}
              </div>
            ) : null}
          </div>
          <NavLink
            to="/goals"
            className={({ isActive }) => (isActive ? 'icon-button active' : 'icon-button')}
            aria-label="Goals"
            title="Goals"
          >
            <Icon iconNode={targetArrow} size={iconSize} aria-hidden="true" />
          </NavLink>
        </nav>

        <div className="layout-account">
          {accountLabel ? <span className="layout-user"><b>{accountLabel}</b></span> : null}
          <button
            type="button"
            className="icon-button chat-open-button"
            onClick={() => setMode('full')}
            aria-label="Open Sakhi Smritika"
            title="Open Sakhi Smritika"
          >
            <MessageCircle size={iconSize} aria-hidden="true" />
          </button>
          <div className="settings-menu" ref={settingsRef}>
            <button
              type="button"
              className="icon-button"
              aria-expanded={settingsOpen}
              aria-label="Settings"
              title="Settings"
              onClick={() => setSettingsOpen((open) => !open)}
            >
              <Settings size={iconSize} aria-hidden="true" />
            </button>
            {settingsOpen ? (
              <div className="settings-dropdown">
                <button
                  type="button"
                  className="icon-button settings-dropdown-item"
                  aria-label="Integrations"
                  title="Integrations"
                  onClick={() => {
                    setSettingsOpen(false)
                    navigate('/settings')
                  }}
                >
                  <Puzzle size={iconSize} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="icon-button settings-dropdown-item"
                  aria-label="Sign out"
                  title="Sign out"
                  onClick={() => {
                    setSettingsOpen(false)
                    setConfirmSignOut(true)
                  }}
                >
                  <LogOut size={iconSize} aria-hidden="true" />
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {confirmSignOut ? (
        <div
          className="layout-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="sign-out-title"
          onClick={() => setConfirmSignOut(false)}
        >
          <div className="layout-modal" onClick={(event) => event.stopPropagation()}>
            <h2 id="sign-out-title" className="layout-modal-title">
              Sign out?
            </h2>
            <p className="layout-modal-text">
              You will need to sign in again to access your account.
            </p>
            <div className="layout-modal-actions">
              <button
                type="button"
                className="layout-modal-button"
                onClick={() => setConfirmSignOut(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="layout-modal-button layout-modal-button-primary"
                onClick={() => {
                  setConfirmSignOut(false)
                  void signOut()
                }}
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <main className="layout-content">
        <Outlet />
      </main>

      <ChatPanel />
    </>
  )
}
