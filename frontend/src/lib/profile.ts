import { supabase } from './supabase'

export type Profile = {
  id: string
  username: string | null
  display_name: string | null
  full_name: string | null
  user_information: string | null
  system_instructions: string | null
  created_at: string
  updated_at: string
}

export async function getProfile(userId: string): Promise<Profile | null> {
  const { data, error } = await supabase
    .from('users')
    .select(
      'id, username, display_name, full_name, user_information, system_instructions, created_at, updated_at',
    )
    .eq('id', userId)
    .maybeSingle()

  if (error) {
    throw error
  }

  return data
}

export async function updateProfile(params: {
  userId: string
  fullName: string
  userInformation: string
  systemInstructions: string
}): Promise<Profile> {
  const { userId, fullName, userInformation, systemInstructions } = params

  const { data, error } = await supabase
    .from('users')
    .update({
      full_name: fullName.trim() || null,
      user_information: userInformation.trim() || null,
      system_instructions: systemInstructions.trim() || null,
    })
    .eq('id', userId)
    .select(
      'id, username, display_name, full_name, user_information, system_instructions, created_at, updated_at',
    )
    .single()

  if (error) {
    throw error
  }

  return data
}
