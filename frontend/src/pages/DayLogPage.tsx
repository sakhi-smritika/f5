import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getEntryByDate, saveDayLog, type DayLog } from '../lib/diary'
import './DayLogPage.css'

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

const HOURS = Array.from({ length: 24 }, (_, hour) => hour)

function emptyDayLog(): DayLog {
  const log: DayLog = {}
  for (const hour of HOURS) {
    log[String(hour)] = ''
  }
  return log
}

function hourLabel(hour: number): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${pad(hour)}:00 – ${pad(hour + 1)}:00`
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function DayLogPage() {
  const { user } = useAuth()
  const [date, setDate] = useState<string>(todayIsoDate)
  const [entryId, setEntryId] = useState<string | null>(null)
  const [dayLog, setDayLog] = useState<DayLog>(emptyDayLog)
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
        setDayLog({ ...emptyDayLog(), ...(entry?.day_log ?? {}) })
      } catch (error) {
        if (cancelled) {
          return
        }
        setEntryId(null)
        setDayLog(emptyDayLog())
        setLoadError(error instanceof Error ? error.message : 'Failed to load day log')
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

  const handleHourChange = useCallback((hour: number, value: string) => {
    setDayLog((current) => ({ ...current, [String(hour)]: value }))
    setSaveStatus((status) => (status === 'idle' ? status : 'idle'))
  }, [])

  const handleSave = useCallback(async () => {
    if (!user?.id) {
      setSaveStatus('error')
      setSaveError('You must be signed in to save.')
      return
    }

    setSaveStatus('saving')
    setSaveError(null)

    try {
      const saved = await saveDayLog({
        date,
        dayLog,
        userId: user.id,
      })
      setEntryId(saved.id)
      setDayLog({ ...emptyDayLog(), ...(saved.day_log ?? {}) })
      setSaveStatus('saved')
    } catch (error) {
      setSaveStatus('error')
      setSaveError(error instanceof Error ? error.message : 'Failed to save day log')
    }
  }, [date, dayLog, user])

  return (
    <div className="daylog-page">
      <div className="daylog-toolbar">
        <h1 className="daylog-title">Day Log</h1>
        <label className="daylog-date">
          <span>Date</span>
          <div className="daylog-date-controls">
            <button
              type="button"
              className="daylog-date-nav"
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
              className="daylog-date-nav"
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
        <p className="daylog-status">Loading...</p>
      ) : loadError ? (
        <p className="daylog-error">{loadError}</p>
      ) : (
        <>
          {entryId === null ? (
            <p className="daylog-hint">No log yet for this date. Fill in the hours below.</p>
          ) : null}
          <div className="daylog-grid">
            {HOURS.map((hour) => (
              <div className="daylog-row" key={hour}>
                <span className="daylog-hour">{hourLabel(hour)}</span>
                <textarea
                  className="daylog-input"
                  rows={1}
                  value={dayLog[String(hour)] ?? ''}
                  placeholder="What did you do?"
                  onChange={(event) => handleHourChange(hour, event.target.value)}
                />
              </div>
            ))}
          </div>
          <div className="daylog-actions">
            <button
              type="button"
              className="daylog-save"
              onClick={() => void handleSave()}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Saving...' : 'Save'}
            </button>
            {saveStatus === 'saved' ? <span className="daylog-saved">Saved</span> : null}
            {saveStatus === 'error' && saveError ? (
              <span className="daylog-error">{saveError}</span>
            ) : null}
          </div>
        </>
      )}
    </div>
  )
}
