import { supabase } from './supabase'

export type Goal = {
  id: string
  goal_name: string
  goal_description: string | null
  progress: string | null
  parent_goal: string | null
  user_id: string
  created_at: string
  updated_at: string
}

export async function listGoals(): Promise<Goal[]> {
  const { data, error } = await supabase
    .from('goals')
    .select('*')
    .order('created_at', { ascending: false })

  if (error) {
    throw error
  }

  return data ?? []
}

export async function getGoal(id: string): Promise<Goal | null> {
  const { data, error } = await supabase.from('goals').select('*').eq('id', id).maybeSingle()

  if (error) {
    throw error
  }

  return data
}

export async function listChildGoals(parentId: string): Promise<Goal[]> {
  const { data, error } = await supabase
    .from('goals')
    .select('*')
    .eq('parent_goal', parentId)
    .order('created_at', { ascending: false })

  if (error) {
    throw error
  }

  return data ?? []
}

export async function createGoal(params: {
  goalName: string
  goalDescription?: string
  progress?: string
  parentGoal?: string | null
  userId: string
}): Promise<Goal> {
  const { goalName, goalDescription, progress, parentGoal, userId } = params

  const { data, error } = await supabase
    .from('goals')
    .insert({
      goal_name: goalName,
      goal_description: goalDescription ?? null,
      progress: progress ?? null,
      parent_goal: parentGoal ?? null,
      user_id: userId,
    })
    .select('*')
    .single()

  if (error) {
    throw error
  }

  return data
}

export async function updateGoal(params: {
  id: string
  goalName: string
  goalDescription: string
  progress: string
}): Promise<Goal> {
  const { id, goalName, goalDescription, progress } = params

  const { data, error } = await supabase
    .from('goals')
    .update({
      goal_name: goalName,
      goal_description: goalDescription || null,
      progress: progress || null,
    })
    .eq('id', id)
    .select('*')
    .single()

  if (error) {
    throw error
  }

  return data
}

export async function deleteGoal(id: string): Promise<void> {
  const { error } = await supabase.from('goals').delete().eq('id', id)

  if (error) {
    throw error
  }
}

export function buildBreadcrumb(goals: Goal[], goalId: string): Goal[] {
  const byId = new Map(goals.map((goal) => [goal.id, goal]))
  const trail: Goal[] = []
  let current = byId.get(goalId)

  while (current) {
    trail.unshift(current)
    current = current.parent_goal ? byId.get(current.parent_goal) : undefined
  }

  return trail
}
