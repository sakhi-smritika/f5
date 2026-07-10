import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getEntryByDate, saveEntry } from '../lib/diary'
import './DiaryPage.css'

function todayIsoDate(): string {
  const now = new Date()
  const offsetMs = now.getTimezoneOffset() * 60 * 1000
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10)
}

function addDays(isoDate: string, delta: number): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  const shifted = new Date(year, month - 1, day + delta)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${shifted.getFullYear()}-${pad(shifted.getMonth() + 1)}-${pad(shifted.getDate())}`
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function DiaryPage() {
  const { user } = useAuth()
  const [date, setDate] = useState<string>(todayIsoDate)
  const [entryId, setEntryId] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setLoadError(null)
      setSaveStatus('idle')
      setSaveError(null)

      try {
        const entry = await getEntryByDate(date)
        if (cancelled) {
          return
        }
        setEntryId(entry?.id ?? null)
        setContent(entry?.general_content ?? '')
      } catch (error) {
        if (cancelled) {
          return
        }
        setEntryId(null)
        setContent('')
        setLoadError(error instanceof Error ? error.message : 'Failed to load entry')
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [date])

  const handleSave = useCallback(async () => {
    if (!user?.id) {
      setSaveStatus('error')
      setSaveError('You must be signed in to save.')
      return
    }

    setSaveStatus('saving')
    setSaveError(null)

    try {
      const saved = await saveEntry({
        date,
        generalContent: content,
        userId: user.id,
      })
      setEntryId(saved.id)
      setContent(saved.general_content ?? '')
      setSaveStatus('saved')
    } catch (error) {
      setSaveStatus('error')
      setSaveError(error instanceof Error ? error.message : 'Failed to save entry')
    }
  }, [content, date, user])

  return (
    <div className="diary-page">
      <div className="diary-toolbar">
        <h1 className="diary-title">Diary</h1>
        <label className="diary-date">
          <span>Date</span>
          <div className="diary-date-controls">
            <button
              type="button"
              className="diary-date-nav"
              aria-label="Previous day"
              onClick={() => setDate((current) => addDays(current, -1))}
            >
              &lt;
            </button>
            <input
              type="date"
              value={date}
              max={todayIsoDate()}
              onChange={(event) => setDate(event.target.value)}
            />
            <button
              type="button"
              className="diary-date-nav"
              aria-label="Next day"
              disabled={date >= todayIsoDate()}
              onClick={() => setDate((current) => addDays(current, 1))}
            >
              &gt;
            </button>
          </div>
        </label>
      </div>

      {loading ? (
        <p className="diary-status">Loading...</p>
      ) : loadError ? (
        <p className="diary-error">{loadError}</p>
      ) : (
        <>
          {entryId === null ? (
            <p className="diary-hint">No entry yet for this date. Start writing below.</p>
          ) : null}
          <textarea
            className="diary-editor"
            value={content}
            placeholder="What's on your mind today?"
            onChange={(event) => {
              setContent(event.target.value)
              if (saveStatus !== 'idle') {
                setSaveStatus('idle')
              }
            }}
          />
          <div className="diary-actions">
            <button
              type="button"
              className="diary-save"
              onClick={() => void handleSave()}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Saving...' : 'Save'}
            </button>
            {saveStatus === 'saved' ? (
              <span className="diary-saved">Saved</span>
            ) : null}
            {saveStatus === 'error' && saveError ? (
              <span className="diary-error">{saveError}</span>
            ) : null}
          </div>
        </>
      )}
    </div>
  )
}
