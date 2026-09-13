import { computed, ref, watch } from 'vue'
import type { ChatMessage, ChatSession } from '../types/chat'

export const STORAGE_KEY = 'mewhelp.chatSessions'

function isChatMessage(value: unknown): value is ChatMessage {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const message = value as Record<string, unknown>
  return (
    typeof message.id === 'string' &&
    (message.role === 'user' || message.role === 'assistant') &&
    typeof message.content === 'string' &&
    (message.status === 'complete' || message.status === 'streaming' || message.status === 'error')
  )
}

function isChatSession(value: unknown): value is ChatSession {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const session = value as Record<string, unknown>
  return (
    typeof session.id === 'string' &&
    typeof session.title === 'string' &&
    typeof session.preview === 'string' &&
    Array.isArray(session.messages) &&
    session.messages.every(isChatMessage)
  )
}

function restoreSessions(): ChatSession[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      return []
    }

    const parsed: unknown = JSON.parse(stored)
    return Array.isArray(parsed) && parsed.every(isChatSession) ? parsed : []
  } catch {
    return []
  }
}

export function createSessionId(): string {
  const randomUuid = globalThis.crypto?.randomUUID
  if (typeof randomUuid === 'function') {
    return randomUuid.call(globalThis.crypto)
  }

  return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function useChatSessions() {
  const sessions = ref<ChatSession[]>(restoreSessions())
  const activeSessionId = ref<string | null>(sessions.value[0]?.id ?? null)
  const currentSession = computed(
    () => sessions.value.find((session) => session.id === activeSessionId.value) ?? null,
  )

  const persistSessions = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.value))
    } catch {
      // Browser storage may be unavailable; in-memory sessions remain usable.
    }
  }

  const createSession = (): ChatSession => {
    const session: ChatSession = {
      id: createSessionId(),
      title: '新对话',
      preview: '',
      messages: [],
    }
    sessions.value.push(session)
    activeSessionId.value = session.id
    return session
  }

  const activateSession = (id: string): void => {
    if (sessions.value.some((session) => session.id === id)) {
      activeSessionId.value = id
    }
  }

  watch(sessions, persistSessions, { deep: true, flush: 'sync' })

  if (sessions.value.length === 0) {
    createSession()
  }

  return {
    sessions,
    activeSessionId,
    currentSession,
    createSession,
    activateSession,
    persistSessions,
  }
}
