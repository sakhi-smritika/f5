import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './Layout.css'

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
]

export function Layout() {
  const { user, signOut } = useAuth()
  const [openCategory, setOpenCategory] = useState<string | null>(null)
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
          {user?.email ? <span className="layout-user">{user.email}</span> : null}
          <button type="button" className="sign-out" onClick={() => void signOut()}>
            Sign out
          </button>
        </div>
      </header>

      <main className="layout-content">
        <Outlet />
      </main>
    </>
  )
}
