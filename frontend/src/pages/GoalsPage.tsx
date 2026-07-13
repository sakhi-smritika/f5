import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronRight, CirclePlus, Trash2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import {
  buildBreadcrumb,
  createGoal,
  deleteGoal,
  getGoal,
  listChildGoals,
  listGoals,
  updateGoal,
  type Goal,
} from '../lib/goals'
import './GoalsPage.css'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

function GoalFormFields(props: {
  goalName: string
  goalDescription: string
  progress: string
  onGoalNameChange: (value: string) => void
  onGoalDescriptionChange: (value: string) => void
  onProgressChange: (value: string) => void
}) {
  const {
    goalName,
    goalDescription,
    progress,
    onGoalNameChange,
    onGoalDescriptionChange,
    onProgressChange,
  } = props

  return (
    <div className="goals-form-fields">
      <label className="goals-field">
        <span className="goals-field-label">Name</span>
        <input
          className="goals-input"
          type="text"
          value={goalName}
          placeholder="Goal name"
          onChange={(event) => onGoalNameChange(event.target.value)}
        />
      </label>
      <label className="goals-field">
        <span className="goals-field-label">Description</span>
        <textarea
          className="goals-textarea"
          value={goalDescription}
          placeholder="What does this goal mean to you?"
          onChange={(event) => onGoalDescriptionChange(event.target.value)}
        />
      </label>
      <label className="goals-field">
        <span className="goals-field-label">Progress</span>
        <textarea
          className="goals-textarea goals-progress-input"
          value={progress}
          placeholder="Where are you with this goal?"
          onChange={(event) => onProgressChange(event.target.value)}
        />
      </label>
    </div>
  )
}

function GoalsListView() {
  const { user } = useAuth()
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [goalName, setGoalName] = useState('')
  const [goalDescription, setGoalDescription] = useState('')
  const [progress, setProgress] = useState('')
  const [createStatus, setCreateStatus] = useState<SaveStatus>('idle')
  const [createError, setCreateError] = useState<string | null>(null)

  const loadGoals = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const next = await listGoals()
      setGoals(next)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load goals')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadGoals()
  }, [loadGoals])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()

    if (!user?.id) {
      setCreateStatus('error')
      setCreateError('You must be signed in to create a goal.')
      return
    }

    const trimmedName = goalName.trim()
    if (!trimmedName) {
      setCreateStatus('error')
      setCreateError('Goal name is required.')
      return
    }

    setCreateStatus('saving')
    setCreateError(null)

    try {
      await createGoal({
        goalName: trimmedName,
        goalDescription,
        progress,
        userId: user.id,
      })
      setGoalName('')
      setGoalDescription('')
      setProgress('')
      setShowCreateForm(false)
      setCreateStatus('idle')
      await loadGoals()
    } catch (error) {
      setCreateStatus('error')
      setCreateError(error instanceof Error ? error.message : 'Failed to create goal')
    }
  }

  const goalsById = new Map(goals.map((goal) => [goal.id, goal]))

  return (
    <div className="goals-page">
      <div className="goals-toolbar">
        <h1 className="goals-title">Goals</h1>
        <button
          type="button"
          className="goals-add-button"
          onClick={() => setShowCreateForm((open) => !open)}
          aria-label="New goal"
          title="New goal"
        >
          <CirclePlus size={24} aria-hidden="true" />
        </button>
      </div>

      {showCreateForm ? (
        <form className="goals-card goals-create-form" onSubmit={(event) => void handleCreate(event)}>
          <h2 className="goals-card-title">New goal</h2>
          <GoalFormFields
            goalName={goalName}
            goalDescription={goalDescription}
            progress={progress}
            onGoalNameChange={setGoalName}
            onGoalDescriptionChange={setGoalDescription}
            onProgressChange={setProgress}
          />
          <div className="goals-actions">
            <button
              type="submit"
              className="goals-button goals-button-primary"
              disabled={createStatus === 'saving'}
            >
              {createStatus === 'saving' ? 'Creating...' : 'Create goal'}
            </button>
            <button
              type="button"
              className="goals-button"
              onClick={() => {
                setShowCreateForm(false)
                setCreateStatus('idle')
                setCreateError(null)
              }}
            >
              Cancel
            </button>
            {createStatus === 'error' && createError ? (
              <span className="goals-error">{createError}</span>
            ) : null}
          </div>
        </form>
      ) : null}

      {loading ? (
        <p className="goals-status">Loading...</p>
      ) : loadError ? (
        <p className="goals-error">{loadError}</p>
      ) : goals.length === 0 ? (
        <div className="goals-empty">
          <p className="goals-empty-text">Create your first goal</p>
          <button
            type="button"
            className="goals-add-button"
            onClick={() => setShowCreateForm(true)}
            aria-label="Create goal"
            title="Create goal"
          >
            <CirclePlus size={24} aria-hidden="true" />
          </button>
        </div>
      ) : (
        <ul className="goals-list">
          {goals.map((goal) => {
            const parent = goal.parent_goal ? goalsById.get(goal.parent_goal) : null
            return (
              <li key={goal.id}>
                <Link className="goals-list-item" to={`/goals/${goal.id}`}>
                  <span className="goals-list-name">{goal.goal_name}</span>
                  {parent ? (
                    <span className="goals-list-parent">under {parent.goal_name}</span>
                  ) : null}
                  {goal.progress ? (
                    <span className="goals-list-progress">{goal.progress}</span>
                  ) : null}
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function GoalDetailView({ goalId }: { goalId: string }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [goal, setGoal] = useState<Goal | null>(null)
  const [children, setChildren] = useState<Goal[]>([])
  const [allGoals, setAllGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [goalName, setGoalName] = useState('')
  const [goalDescription, setGoalDescription] = useState('')
  const [progress, setProgress] = useState('')
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)
  const [showChildForm, setShowChildForm] = useState(false)
  const [childName, setChildName] = useState('')
  const [childDescription, setChildDescription] = useState('')
  const [childProgress, setChildProgress] = useState('')
  const [childCreateStatus, setChildCreateStatus] = useState<SaveStatus>('idle')
  const [childCreateError, setChildCreateError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteStatus, setDeleteStatus] = useState<SaveStatus>('idle')
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loadGoal = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [nextGoal, nextChildren, nextAllGoals] = await Promise.all([
        getGoal(goalId),
        listChildGoals(goalId),
        listGoals(),
      ])

      if (!nextGoal) {
        setLoadError('Goal not found.')
        setGoal(null)
        return
      }

      setGoal(nextGoal)
      setChildren(nextChildren)
      setAllGoals(nextAllGoals)
      setGoalName(nextGoal.goal_name)
      setGoalDescription(nextGoal.goal_description ?? '')
      setProgress(nextGoal.progress ?? '')
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load goal')
    } finally {
      setLoading(false)
    }
  }, [goalId])

  useEffect(() => {
    void loadGoal()
  }, [loadGoal])

  async function handleSave() {
    if (!goal) {
      return
    }

    const trimmedName = goalName.trim()
    if (!trimmedName) {
      setSaveStatus('error')
      setSaveError('Goal name is required.')
      return
    }

    setSaveStatus('saving')
    setSaveError(null)

    try {
      const saved = await updateGoal({
        id: goal.id,
        goalName: trimmedName,
        goalDescription,
        progress,
      })
      setGoal(saved)
      setGoalName(saved.goal_name)
      setGoalDescription(saved.goal_description ?? '')
      setProgress(saved.progress ?? '')
      setSaveStatus('saved')
      setAllGoals((current) => current.map((item) => (item.id === saved.id ? saved : item)))
    } catch (error) {
      setSaveStatus('error')
      setSaveError(error instanceof Error ? error.message : 'Failed to save goal')
    }
  }

  async function handleCreateChild(event: FormEvent) {
    event.preventDefault()

    if (!user?.id || !goal) {
      setChildCreateStatus('error')
      setChildCreateError('You must be signed in to create a goal.')
      return
    }

    const trimmedName = childName.trim()
    if (!trimmedName) {
      setChildCreateStatus('error')
      setChildCreateError('Goal name is required.')
      return
    }

    setChildCreateStatus('saving')
    setChildCreateError(null)

    try {
      const created = await createGoal({
        goalName: trimmedName,
        goalDescription: childDescription,
        progress: childProgress,
        parentGoal: goal.id,
        userId: user.id,
      })
      setChildren((current) => [created, ...current])
      setAllGoals((current) => [created, ...current])
      setChildName('')
      setChildDescription('')
      setChildProgress('')
      setShowChildForm(false)
      setChildCreateStatus('idle')
    } catch (error) {
      setChildCreateStatus('error')
      setChildCreateError(error instanceof Error ? error.message : 'Failed to create child goal')
    }
  }

  async function handleDelete() {
    if (!goal) {
      return
    }

    setDeleteStatus('saving')
    setDeleteError(null)

    try {
      const parentId = goal.parent_goal
      await deleteGoal(goal.id)
      setConfirmDelete(false)
      navigate(parentId ? `/goals/${parentId}` : '/goals')
    } catch (error) {
      setDeleteStatus('error')
      setDeleteError(error instanceof Error ? error.message : 'Failed to delete goal')
    }
  }

  const breadcrumb = goal ? buildBreadcrumb(allGoals, goal.id) : []

  return (
    <div className="goals-page">
      <nav className="goals-breadcrumb" aria-label="Breadcrumb">
        <Link className="goals-breadcrumb-link" to="/goals">
          Goals
        </Link>
        {breadcrumb.map((item, index) => {
          const isLast = index === breadcrumb.length - 1
          return (
            <span key={item.id} className="goals-breadcrumb-segment">
              <ChevronRight size={16} className="goals-breadcrumb-chevron" aria-hidden="true" />
              {isLast ? (
                <span className="goals-breadcrumb-current">{item.goal_name}</span>
              ) : (
                <Link className="goals-breadcrumb-link" to={`/goals/${item.id}`}>
                  {item.goal_name}
                </Link>
              )}
            </span>
          )
        })}
      </nav>

      {loading ? (
        <p className="goals-status">Loading...</p>
      ) : loadError ? (
        <p className="goals-error">{loadError}</p>
      ) : goal ? (
        <>
          <div className="goals-card">
            <GoalFormFields
              goalName={goalName}
              goalDescription={goalDescription}
              progress={progress}
              onGoalNameChange={(value) => {
                setGoalName(value)
                if (saveStatus !== 'idle') {
                  setSaveStatus('idle')
                }
              }}
              onGoalDescriptionChange={(value) => {
                setGoalDescription(value)
                if (saveStatus !== 'idle') {
                  setSaveStatus('idle')
                }
              }}
              onProgressChange={(value) => {
                setProgress(value)
                if (saveStatus !== 'idle') {
                  setSaveStatus('idle')
                }
              }}
            />
            <div className="goals-actions">
              <button
                type="button"
                className="goals-button goals-button-primary"
                onClick={() => void handleSave()}
                disabled={saveStatus === 'saving'}
              >
                {saveStatus === 'saving' ? 'Saving...' : 'Save'}
              </button>
              {saveStatus === 'saved' ? <span className="goals-saved">Saved</span> : null}
              {saveStatus === 'error' && saveError ? (
                <span className="goals-error">{saveError}</span>
              ) : null}
              <button
                type="button"
                className="goals-button goals-button-danger"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2 size={16} aria-hidden="true" />
                Delete
              </button>
            </div>
          </div>

          <section className="goals-children">
            <div className="goals-children-header">
              <h2 className="goals-section-title">Child goals</h2>
              <button
                type="button"
                className="goals-add-button"
                onClick={() => setShowChildForm((open) => !open)}
                aria-label="Add child goal"
                title="Add child goal"
              >
                <CirclePlus size={24} aria-hidden="true" />
              </button>
            </div>

            {showChildForm ? (
              <form
                className="goals-card goals-create-form"
                onSubmit={(event) => void handleCreateChild(event)}
              >
                <GoalFormFields
                  goalName={childName}
                  goalDescription={childDescription}
                  progress={childProgress}
                  onGoalNameChange={setChildName}
                  onGoalDescriptionChange={setChildDescription}
                  onProgressChange={setChildProgress}
                />
                <div className="goals-actions">
                  <button
                    type="submit"
                    className="goals-button goals-button-primary"
                    disabled={childCreateStatus === 'saving'}
                  >
                    {childCreateStatus === 'saving' ? 'Creating...' : 'Create child goal'}
                  </button>
                  <button
                    type="button"
                    className="goals-button"
                    onClick={() => {
                      setShowChildForm(false)
                      setChildCreateStatus('idle')
                      setChildCreateError(null)
                    }}
                  >
                    Cancel
                  </button>
                  {childCreateStatus === 'error' && childCreateError ? (
                    <span className="goals-error">{childCreateError}</span>
                  ) : null}
                </div>
              </form>
            ) : null}

            {children.length === 0 ? (
              <p className="goals-hint">No child goals yet.</p>
            ) : (
              <ul className="goals-list">
                {children.map((child) => (
                  <li key={child.id}>
                    <Link className="goals-list-item" to={`/goals/${child.id}`}>
                      <span className="goals-list-name">{child.goal_name}</span>
                      {child.progress ? (
                        <span className="goals-list-progress">{child.progress}</span>
                      ) : null}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      {confirmDelete ? (
        <div
          className="goals-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-goal-title"
          onClick={() => setConfirmDelete(false)}
        >
          <div className="goals-modal" onClick={(event) => event.stopPropagation()}>
            <h2 id="delete-goal-title" className="goals-modal-title">
              Delete goal?
            </h2>
            <p className="goals-modal-text">
              This will permanently delete &ldquo;{goal?.goal_name}&rdquo; and all of its child goals.
            </p>
            <div className="goals-modal-actions">
              <button
                type="button"
                className="goals-button"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="goals-button goals-button-danger"
                onClick={() => void handleDelete()}
                disabled={deleteStatus === 'saving'}
              >
                {deleteStatus === 'saving' ? 'Deleting...' : 'Delete'}
              </button>
            </div>
            {deleteStatus === 'error' && deleteError ? (
              <p className="goals-error">{deleteError}</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function GoalsPage() {
  const { goalId } = useParams()

  if (goalId) {
    return <GoalDetailView goalId={goalId} />
  }

  return <GoalsListView />
}
