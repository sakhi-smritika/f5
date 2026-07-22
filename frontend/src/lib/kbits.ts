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

export async function deleteKbit(id: string): Promise<void> {
  const { error } = await supabase.from('knowledge_bits').delete().eq('id', id)
  if (error) {
    throw error
  }
}
