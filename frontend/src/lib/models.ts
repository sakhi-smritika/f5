import { apiFetch } from './api'

export type ChatModel = {
  id: string
  label: string
  is_default: boolean
}

export type ChatModelsResponse = {
  default: string
  models: ChatModel[]
}

export async function listChatModels(): Promise<ChatModelsResponse> {
  const response = await apiFetch('/api/v1/models')
  if (!response.ok) {
    throw new Error('Failed to load chat models')
  }
  return response.json() as Promise<ChatModelsResponse>
}

const STORAGE_KEY = 'f5-chat-model'

export function getStoredChatModel(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function setStoredChatModel(modelId: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, modelId)
  } catch {
    // Ignore quota / private-mode failures.
  }
}
