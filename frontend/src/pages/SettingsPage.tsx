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

  const isBusy = actionStatus === 'loading'

  return (
    <div className="settings-page">
      <header className="settings-header">
        <h1 className="settings-title">Settings</h1>
        <p className="settings-subtitle">
          Connect services so Sakhi Smritika can help with your schedule and tasks.
        </p>
      </header>

      {flashMessage ? <p className="settings-flash">{flashMessage}</p> : null}
      {loadError ? <p className="settings-error">{loadError}</p> : null}
      {actionError ? <p className="settings-error">{actionError}</p> : null}

      <section className="settings-card">
        <div className="settings-card-header">
          <div>
            <h2 className="settings-card-title">Google Workspace</h2>
            <p className="settings-card-description">
              Link Calendar and Tasks so the assistant can answer questions like
              &ldquo;What&rsquo;s on my calendar tomorrow?&rdquo; or &ldquo;Add a task to call the bank.&rdquo;
            </p>
          </div>
          <span
            className={
              status?.connected ? 'settings-badge settings-badge-connected' : 'settings-badge'
            }
          >
            {status?.connected ? 'Connected' : 'Not connected'}
          </span>
        </div>

        {status?.connected && status.google_email ? (
          <p className="settings-connected-as">
            Connected as <strong>{status.google_email}</strong>
          </p>
        ) : (
          <p className="settings-connected-as">
            Not connected yet. You&rsquo;ll be sent to Google to approve access.
          </p>
        )}

        <div className="settings-card-actions">
          {status?.connected ? (
            <button
              type="button"
              className="settings-button settings-button-secondary"
              onClick={() => void handleDisconnect()}
              disabled={isBusy}
            >
              {isBusy ? 'Working…' : 'Disconnect'}
            </button>
          ) : (
            <button
              type="button"
              className="settings-button settings-button-primary"
              onClick={() => void handleConnect()}
              disabled={isBusy || Boolean(loadError)}
            >
              {isBusy ? 'Redirecting…' : 'Connect Google'}
            </button>
          )}
        </div>
      </section>
    </div>
  )
}
