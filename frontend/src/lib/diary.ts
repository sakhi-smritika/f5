import { supabase } from './supabase'

export type DayLog = Record<string, string>

export type DiaryEntry = {
  id: string
  date: string
  how_was_the_day: string | null
  major_events: string | null
  general_content: string | null
  day_log: DayLog | null
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
  howWasTheDay: string
  majorEvents: string
  generalContent: string
  userId: string
}): Promise<DiaryEntry> {
  const { date, howWasTheDay, majorEvents, generalContent, userId } = params

  const { data, error } = await supabase
    .from('diary')
    .upsert(
      {
        date,
        how_was_the_day: howWasTheDay,
        major_events: majorEvents,
        general_content: generalContent,
        user_id: userId,
      },
      { onConflict: 'user_id,date' },
    )
    .select('*')
    .single()

  if (error) {
    throw error
  }

  return data
}

export async function saveDayLog(params: {
  date: string
  dayLog: DayLog
  userId: string
}): Promise<DiaryEntry> {
  const { date, dayLog, userId } = params

  const { data, error } = await supabase
    .from('diary')
    .upsert(
      { date, day_log: dayLog, user_id: userId },
      { onConflict: 'user_id,date' },
    )
    .select('*')
    .single()

  if (error) {
    throw error
  }

  return data
}
