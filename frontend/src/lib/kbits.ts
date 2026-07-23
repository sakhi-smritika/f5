import { apiFetch } from './api'
import { supabase } from './supabase'

export type KnowledgeBit = {
  id: string
  created_at: string
  updated_at: string
  title: string
  content: string
  related_goal: string | null
  is_read: boolean
  is_liked: boolean
  is_disliked: boolean
  rating: number | null
  is_marked_relavant: boolean
  is_marked_irrelavant: boolean
}

const KBIT_COLUMNS =
  'id, created_at, updated_at, title, content, related_goal, is_read, ' +
  'is_liked, is_disliked, rating, is_marked_relavant, is_marked_irrelavant'

// The feed is read straight from Supabase (RLS scopes it to the user), matching
// how conversations and goals are loaded elsewhere.
export async function listKbits(options: { unreadOnly?: boolean } = {}): Promise<KnowledgeBit[]> {
  let query = supabase
    .from('knowledge_bits')
    .select(KBIT_COLUMNS)
    .order('created_at', { ascending: false })

  if (options.unreadOnly) {
    query = query.eq('is_read', false)
  }

  const { data, error } = await query
  if (error) {
    throw error
  }
  return (data ?? []) as unknown as KnowledgeBit[]
}

// Fetch a single bit (RLS-scoped) so the chat window can pin its content at the
// top of a discussion thread.
export async function getKbitById(id: string): Promise<KnowledgeBit | null> {
  const { data, error } = await supabase
    .from('knowledge_bits')
    .select(KBIT_COLUMNS)
    .eq('id', id)
    .limit(1)
    .maybeSingle()

  if (error) {
    throw error
  }
  return (data as unknown as KnowledgeBit) ?? null
}

export type StageStrategies = {
  default: string | null
  options: string[]
}

export type StrategyCatalog = {
  query: StageStrategies
  source: StageStrategies
  screen: StageStrategies
  rank: StageStrategies
}

export async function getStrategies(): Promise<StrategyCatalog> {
  const response = await apiFetch('/api/v1/kbits/strategies')
  if (!response.ok) {
    throw new Error('Failed to load strategies')
  }
  return response.json()
}

export type InvokeOptions = {
  goalId?: string | null
  count?: number
  queryStrategy?: string | null
  sourceStrategy?: string | null
  screenStrategy?: string | null
  rankStrategy?: string | null
}

export async function invokeKbits(options: InvokeOptions = {}): Promise<KnowledgeBit[]> {
  const body: Record<string, unknown> = {}
  if (options.goalId) body.goal_id = options.goalId
  if (options.count) body.count = options.count
  if (options.queryStrategy) body.query_strategy = options.queryStrategy
  if (options.sourceStrategy) body.source_strategy = options.sourceStrategy
  if (options.screenStrategy) body.screen_strategy = options.screenStrategy
  if (options.rankStrategy) body.rank_strategy = options.rankStrategy

  const response = await apiFetch('/api/v1/kbits/invoke', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = 'Failed to generate knowledge bits'
    try {
      const data = (await response.json()) as { detail?: string }
      if (data.detail) detail = data.detail
    } catch {
      // keep default
    }
    throw new Error(detail)
  }
  const data = (await response.json()) as { bits?: KnowledgeBit[] }
  return data.bits ?? []
}

export type KbitUpdate = Partial<
  Pick<
    KnowledgeBit,
    | 'is_read'
    | 'is_liked'
    | 'is_disliked'
    | 'rating'
    | 'is_marked_relavant'
    | 'is_marked_irrelavant'
  >
>

// Interaction updates and deletes go straight to Supabase (RLS scopes them to
// the owner), matching how goals/diary writes work. This keeps the write on the
// same row the feed read, avoiding any client/DB mismatch with the backend.
export async function updateKbit(id: string, updates: KbitUpdate): Promise<void> {
  const { error } = await supabase.from('knowledge_bits').update(updates).eq('id', id)
  if (error) {
    throw error
  }
}

// Deletion goes through the backend (not straight to Supabase) so the server can
// tear down the bit's discussion ADK session — the DB cascade only removes the
// conversations metadata row, not ADK's own session/event tables.
export async function deleteKbit(id: string): Promise<void> {
  const response = await apiFetch(`/api/v1/kbits/${id}`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error('Failed to delete knowledge bit')
  }
}

// Get or lazily create the discussion conversation for a bit, reusing the chat
// machinery. Returns the conversation id to load/stream comments against via the
// chat lib (loadMessages / streamMessage).
export async function ensureKbitDiscussion(kbitId: string): Promise<string> {
  const response = await apiFetch(`/api/v1/kbits/${kbitId}/discussion`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error('Failed to open discussion')
  }
  const data = (await response.json()) as { conversation_id: string }
  return data.conversation_id
}

// Map of kbit_id -> conversation_id for bits that already have a discussion
// thread. Read straight from Supabase (RLS-scoped) so the feed can show which
// bits are already being discussed without opening each one.
export async function getKbitDiscussionMap(): Promise<Record<string, string>> {
  const { data, error } = await supabase
    .from('conversations')
    .select('id, kbit_id')
    .not('kbit_id', 'is', null)

  if (error) {
    throw error
  }

  const map: Record<string, string> = {}
  for (const row of (data ?? []) as { id: string; kbit_id: string | null }[]) {
    if (row.kbit_id) {
      map[row.kbit_id] = row.id
    }
  }
  return map
}
