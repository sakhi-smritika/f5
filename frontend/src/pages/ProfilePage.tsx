import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getProfile, updateProfile } from '../lib/profile'
import './ProfilePage.css'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function ProfilePage() {
  const { user } = useAuth()
  const [fullName, setFullName] = useState('')
  const [userInformation, setUserInformation] = useState('')
  const [systemInstructions, setSystemInstructions] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    if (!user?.id) {
      setLoading(false)
      return
    }

    setLoading(true)
    setLoadError(null)

    try {
      const profile = await getProfile(user.id)
      setFullName(profile?.full_name ?? '')
      setUserInformation(profile?.user_information ?? '')
      setSystemInstructions(profile?.system_instructions ?? '')
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }, [user?.id])

  useEffect(() => {
    void loadProfile()
  }, [loadProfile])

  async function handleSave() {
    if (!user?.id) {
      setSaveStatus('error')
      setSaveError('You must be signed in to save your profile.')
      return
    }

    setSaveStatus('saving')
    setSaveError(null)

    try {
      const saved = await updateProfile({
        userId: user.id,
        fullName,
        userInformation,
        systemInstructions,
      })
      setFullName(saved.full_name ?? '')
      setUserInformation(saved.user_information ?? '')
      setSystemInstructions(saved.system_instructions ?? '')
      setSaveStatus('saved')
    } catch (error) {
      setSaveStatus('error')
      setSaveError(error instanceof Error ? error.message : 'Failed to save profile')
    }
  }

  return (
    <div className="profile-page">
      <header className="profile-header">
        <h1 className="profile-title">Profile</h1>
      </header>

      {loading ? (
        <p className="profile-status">Loading...</p>
      ) : loadError ? (
        <p className="profile-error">{loadError}</p>
      ) : (
        <>
          <label className="profile-field">
            <span className="profile-field-label">Full name</span>
            <input
              className="profile-input"
              type="text"
              value={fullName}
              placeholder="Your full name"
              onChange={(event) => {
                setFullName(event.target.value)
                if (saveStatus !== 'idle') {
                  setSaveStatus('idle')
                }
              }}
            />
          </label>

          <label className="profile-field">
            <span className="profile-field-label">About you</span>
            <textarea
              className="profile-textarea"
              value={userInformation}
              placeholder="Share context the assistant should know about you — background, preferences, current focus, etc."
              onChange={(event) => {
                setUserInformation(event.target.value)
                if (saveStatus !== 'idle') {
                  setSaveStatus('idle')
                }
              }}
            />
          </label>

          <label className="profile-field">
            <span className="profile-field-label">System instructions</span>
            <textarea
              className="profile-textarea profile-instructions-input"
              value={systemInstructions}
              placeholder="How should the assistant behave? Tone, priorities, things to always or never do."
              onChange={(event) => {
                setSystemInstructions(event.target.value)
                if (saveStatus !== 'idle') {
                  setSaveStatus('idle')
                }
              }}
            />
          </label>

          <div className="profile-actions">
            <button
              type="button"
              className="profile-button profile-button-primary"
              onClick={() => void handleSave()}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Saving...' : 'Save'}
            </button>
            {saveStatus === 'saved' ? <span className="profile-saved">Saved</span> : null}
            {saveStatus === 'error' && saveError ? (
              <span className="profile-error">{saveError}</span>
            ) : null}
          </div>
        </>
      )}
    </div>
  )
}
