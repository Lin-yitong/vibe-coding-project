import { afterEach, describe, expect, it, vi } from 'vitest'
import { STORAGE_KEY, useChatSessions } from './useChatSessions'
import type { ChatSession } from '../types/chat'

const savedSession: ChatSession = {
  id: 'saved-session',
  title: '订单咨询',
  preview: '订单还没有发货',
  messages: [
    { id: 'm1', role: 'user', content: '订单还没有发货', status: 'complete' },
  ],
}

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('useChatSessions', () => {
  it('restores saved sessions from localStorage', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([savedSession]))

    const { sessions, currentSession } = useChatSessions()

    expect(sessions.value).toEqual([savedSession])
    expect(currentSession.value?.id).toBe(savedSession.id)
  })

  it('restores interrupted streaming replies as errors and persists the repaired state', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        {
          ...savedSession,
          messages: [
            ...savedSession.messages,
            { id: 'm2', role: 'assistant', content: '正在查询', status: 'streaming' },
          ],
        },
      ]),
    )

    const { sessions } = useChatSessions()

    expect(sessions.value[0]?.messages[1]?.status).toBe('error')
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')[0].messages[1].status).toBe('error')
  })

  it('creates and activates a session with crypto.randomUUID', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'generated-session-id' })
    const { createSession, currentSession, sessions } = useChatSessions()

    const created = createSession()

    expect(created.id).toBe('generated-session-id')
    expect(currentSession.value?.id).toBe('generated-session-id')
    expect(sessions.value).toContainEqual(created)
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toContainEqual(created)
  })

  it('falls back to a timestamp-based ID when randomUUID is unavailable', () => {
    vi.stubGlobal('crypto', {})
    vi.spyOn(Date, 'now').mockReturnValue(12345)
    vi.spyOn(Math, 'random').mockReturnValue(0.5)

    const { createSession } = useChatSessions()

    expect(createSession().id).toBe('session-12345-i')
  })

  it('persists direct message mutations and activates saved sessions', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        savedSession,
        { id: 'other', title: '退款', preview: '', messages: [] },
      ]),
    )
    const { activateSession, currentSession } = useChatSessions()

    activateSession('other')
    currentSession.value?.messages.push({
      id: 'm2',
      role: 'assistant',
      content: '我来帮您处理。',
      status: 'complete',
    })

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as ChatSession[]
    expect(currentSession.value?.id).toBe('other')
    expect(persisted[1].messages).toEqual([
      { id: 'm2', role: 'assistant', content: '我来帮您处理。', status: 'complete' },
    ])
  })
})
