import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'
import { STORAGE_KEY } from './composables/useChatSessions'
import { streamChat } from './api/chatClient'

vi.mock('./api/chatClient', () => ({ streamChat: vi.fn() }))

const mockStream = vi.mocked(streamChat)

async function send(wrapper: ReturnType<typeof mount>, message: string): Promise<void> {
  await wrapper.get('textarea').setValue(message)
  await wrapper.get('form').trigger('submit')
}

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('grows one assistant bubble as deltas arrive and re-enables sending on DONE', async () => {
    mockStream.mockImplementation(async (_request, { onDelta, onDone }) => {
      onDelta('您好')
      onDelta('，请提供订单号')
      onDone()
    })
    const wrapper = mount(App)

    await send(wrapper, '订单未发货')

    expect(wrapper.findAll('[aria-label="客服消息"]')).toHaveLength(1)
    expect(wrapper.text()).toContain('您好，请提供订单号')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('keeps sending disabled while a response streams and completes the bubble on an error', async () => {
    let failStream: ((message: string) => void) | undefined
    mockStream.mockImplementation(async (_request, { onError }) => {
      failStream = onError
    })
    const wrapper = mount(App)

    await send(wrapper, '我要退款')

    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('客服正在处理')

    failStream?.('服务暂时不可用')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('服务暂时不可用')
    expect(wrapper.find('[data-streaming-cursor]').exists()).toBe(false)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('creates sessions and displays the selected session history', async () => {
    mockStream.mockImplementation(async (_request, { onDone }) => onDone())
    const wrapper = mount(App)

    await send(wrapper, '第一段对话')
    await wrapper.get('.chat-header__new').trigger('click')

    expect(wrapper.findAll('[aria-label="用户消息"]')).toHaveLength(0)
    await wrapper.get('[data-session-id]').trigger('click')

    expect(wrapper.findAll('[aria-label="用户消息"]')).toHaveLength(1)
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toHaveLength(2)
  })

  it('starts with the sidebar collapsed on narrow screens and opens it from the header', async () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
    const wrapper = mount(App)

    expect(wrapper.find('.session-sidebar').exists()).toBe(false)

    await wrapper.get('[aria-label="打开会话列表"]').trigger('click')

    expect(wrapper.find('.session-sidebar').exists()).toBe(true)
  })

  it('keeps the sidebar visible without a close action on desktop', () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))
    const wrapper = mount(App)

    expect(wrapper.find('.session-sidebar').exists()).toBe(true)
    expect(wrapper.find('[data-action="close-sidebar"]').exists()).toBe(false)
  })

  it('keeps a session preview on the latest user message after assistant updates', async () => {
    mockStream.mockImplementation(async (_request, { onDelta, onError }) => {
      onDelta('我可以协助处理退款。')
      onError('服务暂时不可用')
    })
    const wrapper = mount(App)

    await send(wrapper, '我要申请退款')

    const persisted = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    expect(persisted[0].preview).toBe('我要申请退款')
  })
})
