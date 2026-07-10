import { supabase } from './supabase'

export type Profile = {
  id: string
  username: string | null
  display_name: string | null
}

export async function getProfile(userId: string): Promise<Profile | null> {
  const { data, error } = await supabase
    .from('users')
    .select('id, username, display_name')
    .eq('id', userId)
    .maybeSingle()

  if (error) {
    throw error
  }

  return data
}
