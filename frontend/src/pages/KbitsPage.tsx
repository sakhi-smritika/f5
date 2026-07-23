import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Check,
  MessageCircle,
  Sparkles,
  SlidersHorizontal,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  X,
} from 'lucide-react'
import {
  deleteKbit,
  getKbitDiscussionMap,
  getStrategies,
  invokeKbits,
  listKbits,
  updateKbit,
  type KbitUpdate,
  type KnowledgeBit,
  type StrategyCatalog,
} from '../lib/kbits'
import { KbitComments } from '../components/kbits/KbitComments'
import './KbitsPage.css'

const STAGES = ['query', 'source', 'screen', 'rank'] as const
type Stage = (typeof STAGES)[number]

export function KbitsPage() {
  const [bits, setBits] = useState<KnowledgeBit[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [showOptions, setShowOptions] = useState(false)
  const [catalog, setCatalog] = useState<StrategyCatalog | null>(null)
  const [selected, setSelected] = useState<Record<Stage, string>>({
    query: '',
    source: '',
    screen: '',
    rank: '',
  })
  const [count, setCount] = useState(5)
  // Bit ids that already have a discussion thread, so the card can show it.
  const [discussed, setDiscussed] = useState<Set<string>>(new Set())

  const cardRefs = useRef(new Map<string, HTMLElement>())
  // Ids we've already tried to auto-mark-read, so a failed PATCH never retries
  // in a loop (each bit is attempted at most once per session).
  const autoReadAttempted = useRef(new Set<string>())

  const loadFeed = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      setBits(await listKbits())
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load knowledge bits')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadFeed()
  }, [loadFeed])

  useEffect(() => {
    getStrategies()
      .then(setCatalog)
      .catch(() => setCatalog(null))
  }, [])

  useEffect(() => {
    getKbitDiscussionMap()
      .then((map) => setDiscussed(new Set(Object.keys(map))))
      .catch(() => setDiscussed(new Set()))
  }, [])

  const markDiscussed = useCallback((id: string) => {
    setDiscussed((current) => {
      if (current.has(id)) {
        return current
      }
      const next = new Set(current)
      next.add(id)
      return next
    })
  }, [])

  const patchBit = useCallback((id: string, updates: KbitUpdate) => {
    let previous: KnowledgeBit | undefined
    setBits((current) =>
      current.map((bit) => {
        if (bit.id === id) {
          previous = bit
          return { ...bit, ...updates }
        }
        return bit
      }),
    )
    // Revert only this bit on failure. Do NOT reload the feed here: a failed
    // auto-read would otherwise reset is_read and retrigger the observer loop.
    void updateKbit(id, updates).catch(() => {
      if (previous) {
        setBits((current) => current.map((bit) => (bit.id === id ? previous! : bit)))
      }
    })
  }, [])

  // Mark a bit read once its card has been on screen.
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
            const id = entry.target.getAttribute('data-bit-id')
            if (!id || autoReadAttempted.current.has(id)) continue
            const bit = bits.find((item) => item.id === id)
            if (bit && !bit.is_read) {
              autoReadAttempted.current.add(id)
              patchBit(id, { is_read: true })
            }
          }
        }
      },
      { threshold: [0.6] },
    )

    for (const element of cardRefs.current.values()) {
      observer.observe(element)
    }
    return () => observer.disconnect()
  }, [bits, patchBit])

  async function handleGenerate() {
    setGenerating(true)
    setGenerateError(null)
    try {
      const created = await invokeKbits({
        count,
        queryStrategy: selected.query || undefined,
        sourceStrategy: selected.source || undefined,
        screenStrategy: selected.screen || undefined,
        rankStrategy: selected.rank || undefined,
      })
      if (created.length > 0) {
        setBits((current) => [...created, ...current])
      } else {
        setGenerateError('No new bits were generated. Try adjusting your goals or options.')
      }
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : 'Failed to generate')
    } finally {
      setGenerating(false)
    }
  }

  function handleDelete(id: string) {
    setBits((current) => current.filter((bit) => bit.id !== id))
    void deleteKbit(id).catch(() => {
      void loadFeed()
    })
  }

  return (
    <div className="kbits-page">
      <div className="kbits-toolbar">
        <h1 className="kbits-title">Knowledge Bits</h1>
        <div className="kbits-toolbar-actions">
          <button
            type="button"
            className={showOptions ? 'kbits-icon-button active' : 'kbits-icon-button'}
            aria-label="Generation options"
            aria-expanded={showOptions}
            title="Generation options"
            onClick={() => setShowOptions((open) => !open)}
          >
            <SlidersHorizontal size={18} aria-hidden="true" />
          </button>
          <button
            type="button"
            className={generating ? 'kbits-icon-button kbits-generating' : 'kbits-icon-button'}
            onClick={() => void handleGenerate()}
            disabled={generating}
            aria-label={generating ? 'Generating' : 'Generate'}
            title={generating ? 'Generating...' : 'Generate'}
          >
            <Sparkles size={18} aria-hidden="true" />
          </button>
        </div>
      </div>

      {showOptions ? (
        <div className="kbits-options">
          <label className="kbits-option">
            <span className="kbits-option-label">Count</span>
            <input
              className="kbits-option-input"
              type="number"
              min={1}
              max={20}
              value={count}
              onChange={(event) => setCount(Number(event.target.value) || 1)}
            />
          </label>
          {catalog
            ? STAGES.map((stage) => {
                const stageCatalog = catalog[stage]
                return (
                  <label key={stage} className="kbits-option">
                    <span className="kbits-option-label">{stage}</span>
                    <select
                      className="kbits-option-input"
                      value={selected[stage]}
                      onChange={(event) =>
                        setSelected((current) => ({ ...current, [stage]: event.target.value }))
                      }
                    >
                      <option value="">
                        Default{stageCatalog.default ? ` (${stageCatalog.default})` : ''}
                      </option>
                      {stageCatalog.options.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </label>
                )
              })
            : null}
        </div>
      ) : null}

      {generateError ? <p className="kbits-error">{generateError}</p> : null}

      {loading ? (
        <p className="kbits-status">Loading...</p>
      ) : loadError ? (
        <p className="kbits-error">{loadError}</p>
      ) : bits.length === 0 ? (
        <div className="kbits-empty">
          <p className="kbits-empty-text">No knowledge bits yet.</p>
          <p className="kbits-empty-hint">
            Tap Generate to get bits tailored to your goals instead of doom-scrolling.
          </p>
        </div>
      ) : (
        <div className="kbits-feed">
          {bits.map((bit) => (
            <KbitCard
              key={bit.id}
              bit={bit}
              registerRef={(element) => {
                if (element) {
                  cardRefs.current.set(bit.id, element)
                } else {
                  cardRefs.current.delete(bit.id)
                }
              }}
              onUpdate={patchBit}
              onDelete={handleDelete}
              hasDiscussion={discussed.has(bit.id)}
              onDiscussionStarted={() => markDiscussed(bit.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function KbitCard(props: {
  bit: KnowledgeBit
  registerRef: (element: HTMLElement | null) => void
  onUpdate: (id: string, updates: KbitUpdate) => void
  onDelete: (id: string) => void
  hasDiscussion: boolean
  onDiscussionStarted: () => void
}) {
  const { bit, registerRef, onUpdate, onDelete, hasDiscussion, onDiscussionStarted } =
    props
  const [showComments, setShowComments] = useState(false)

  return (
    <article className="kbits-card" data-bit-id={bit.id} ref={registerRef}>
      <div className="kbits-card-body">
        <h2 className="kbits-card-title">{bit.title}</h2>
        <p className="kbits-card-content">{bit.content}</p>
      </div>
      <div className="kbits-card-actions">
        <button
          type="button"
          className={bit.is_liked ? 'kbits-action active' : 'kbits-action'}
          aria-pressed={bit.is_liked}
          aria-label="Like"
          title="Like"
          onClick={() =>
            onUpdate(bit.id, { is_liked: !bit.is_liked, is_disliked: false })
          }
        >
          <ThumbsUp size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className={bit.is_disliked ? 'kbits-action active' : 'kbits-action'}
          aria-pressed={bit.is_disliked}
          aria-label="Dislike"
          title="Dislike"
          onClick={() =>
            onUpdate(bit.id, { is_disliked: !bit.is_disliked, is_liked: false })
          }
        >
          <ThumbsDown size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className={bit.is_marked_relavant ? 'kbits-action active' : 'kbits-action'}
          aria-pressed={bit.is_marked_relavant}
          aria-label="Mark relevant"
          title="Mark relevant"
          onClick={() =>
            onUpdate(bit.id, {
              is_marked_relavant: !bit.is_marked_relavant,
              is_marked_irrelavant: false,
            })
          }
        >
          <Check size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className={bit.is_marked_irrelavant ? 'kbits-action active' : 'kbits-action'}
          aria-pressed={bit.is_marked_irrelavant}
          aria-label="Mark irrelevant"
          title="Mark irrelevant"
          onClick={() =>
            onUpdate(bit.id, {
              is_marked_irrelavant: !bit.is_marked_irrelavant,
              is_marked_relavant: false,
            })
          }
        >
          <X size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className={
            showComments || hasDiscussion ? 'kbits-action active' : 'kbits-action'
          }
          aria-pressed={showComments}
          aria-label="Comments"
          title="Comments"
          onClick={() => setShowComments((open) => !open)}
        >
          <MessageCircle size={18} aria-hidden="true" />
          {hasDiscussion ? <span className="kbits-action-dot" aria-hidden="true" /> : null}
        </button>
        <button
          type="button"
          className="kbits-action kbits-action-danger"
          aria-label="Delete"
          title="Delete"
          onClick={() => onDelete(bit.id)}
        >
          <Trash2 size={18} aria-hidden="true" />
        </button>
      </div>
      {showComments ? (
        <KbitComments kbitId={bit.id} onStarted={onDiscussionStarted} />
      ) : null}
    </article>
  )
}
