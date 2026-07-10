import { supabase } from './supabase'

export type DiaryEntry = {
  id: string
  date: string
  general_content: string | null
  created_at: string
  updated_at: string
  user_id: string
}

export async function getEntryByDate(date: string): Promise<DiaryEntry | null> {
  const { data, error } = await supabase
    .from('diary')
    .select('*')
    .eq('date', date)
    .maybeSingle()

  if (error) {
    throw error
  }

  return data
}

export async function saveEntry(params: {
  date: string
  generalContent: string
  userId: string
}): Promise<DiaryEntry> {
  const { date, generalContent, userId } = params

  const { data, error } = await supabase
    .from('diary')
    .upsert(
      { date, general_content: generalContent, user_id: userId },
      { onConflict: 'user_id,date' },
    )
    .select('*')
    .single()

  if (error) {
    throw error
  }

  return data
}
