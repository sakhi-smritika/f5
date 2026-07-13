import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  disconnectGoogle,
  getGoogleAuthorizeUrl,
  getGoogleConnectionStatus,
  type GoogleConnectionStatus,
} from '../lib/integrations'
import './SettingsPage.css'

type ActionStatus = 'idle' | 'loading' | 'error'

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [status, setStatus] = useState<GoogleConnectionStatus | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionStatus, setActionStatus] = useState<ActionStatus>('idle')
  const [actionError, setActionError] = useState<string | null>(null)
  const [flashMessage, setFlashMessage] = useState<string | null>(null)

  const loadStatus = useCallback(async () => {
    setLoadError(null)
    try {
      const next = await getGoogleConnectionStatus()
      setStatus(next)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load settings')
    }
  }, [])

  useEffect(() => {
    void loadStatus()
  }, [loadStatus])

  useEffect(() => {
    const googleResult = searchParams.get('google')
    if (!googleResult) {
      return
    }

    if (googleResult === 'connected') {
      setFlashMessage('Google connected successfully.')
      void loadStatus()
    } else if (googleResult === 'error') {
      const message = searchParams.get('message')
      setFlashMessage(message ? `Google connection failed: ${message}` : 'Google connection failed.')
    }

    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('google')
    nextParams.delete('message')
    setSearchParams(nextParams, { replace: true })
  }, [loadStatus, searchParams, setSearchParams])

  async function handleConnect() {
    setActionStatus('loading')
    setActionError(null)
    try {
      const url = await getGoogleAuthorizeUrl()
      window.location.assign(url)
    } catch (error) {
      setActionStatus('error')
      setActionError(error instanceof Error ? error.message : 'Failed to connect Google')
    }
  }

  async function handleDisconnect() {
    setActionStatus('loading')
    setActionError(null)
    try {
      await disconnectGoogle()
      setStatus({ connected: false, google_email: null })
      setFlashMessage('Google disconnected.')
      setActionStatus('idle')
    } catch (error) {
      setActionStatus('error')
      setActionError(error instanceof Error ? error.message : 'Failed to disconnect Google')
    }
  }

  function handleToggle() {
    if (status?.connected) {
      void handleDisconnect()
    } else {
      void handleConnect()
    }
  }

  const isBusy = actionStatus === 'loading'
  const isConnected = status?.connected ?? false

  return (
    <div className="settings-page">
      <header className="settings-header">
        <h1 className="settings-title">Settings</h1>
      </header>

      {flashMessage ? <p className="settings-flash">{flashMessage}</p> : null}
      {loadError ? <p className="settings-error">{loadError}</p> : null}
      {actionError ? <p className="settings-error">{actionError}</p> : null}

      <div className="settings-row">
        <span className="settings-row-label">Google</span>
        <button
          type="button"
          role="switch"
          className={`settings-switch${isConnected ? ' settings-switch-on' : ''}`}
          aria-checked={isConnected}
          aria-label="Google integration"
          disabled={isBusy || Boolean(loadError)}
          onClick={() => handleToggle()}
        >
          <span className="settings-switch-thumb" />
        </button>
      </div>
    </div>
  )
}
