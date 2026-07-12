import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getProfile } from '../lib/profile'
import { ChatPanel } from './chat/ChatPanel'
import { ChatUIProvider, useChatUI } from './chat/ChatUIContext'
import './Layout.css'

function ChatBubbleIcon() {
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
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8A8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5Z" />
    </svg>
  )
}

function SignOutIcon() {
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
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  )
}

type PaneItem = {
  label: string
  to: string
}

type PaneCategory = {
  label: string
  items: PaneItem[]
}

const paneCategories: PaneCategory[] = [
  {
    label: 'Introspection',
    items: [
      { label: 'Diary', to: '/introspection/diary' },
      { label: 'Day Log', to: '/introspection/day-log' },
    ],
  },
  {
    label: 'Settings',
    items: [{ label: 'Integrations', to: '/settings' }],
  },
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
  const { setMode } = useChatUI()
  const [openCategory, setOpenCategory] = useState<string | null>(null)
  const [confirmSignOut, setConfirmSignOut] = useState(false)
  const [displayName, setDisplayName] = useState<string | null>(null)
  const navRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (navRef.current && !navRef.current.contains(event.target as Node)) {
        setOpenCategory(null)
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
        <nav className="pane-nav" ref={navRef}>
          {paneCategories.map((category) => (
            <div className="pane-category" key={category.label}>
              <button
                type="button"
                className="pane-category-button"
                aria-expanded={openCategory === category.label}
                onClick={() =>
                  setOpenCategory((current) =>
                    current === category.label ? null : category.label,
                  )
                }
              >
                {category.label}
              </button>
              {openCategory === category.label ? (
                <div className="pane-menu">
                  {category.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        isActive ? 'pane-menu-item active' : 'pane-menu-item'
                      }
                      onClick={() => setOpenCategory(null)}
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
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
            <ChatBubbleIcon />
          </button>
          <button
            type="button"
            className="icon-button sign-out"
            onClick={() => setConfirmSignOut(true)}
            aria-label="Sign out"
            title="Sign out"
          >
            <SignOutIcon />
          </button>
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
