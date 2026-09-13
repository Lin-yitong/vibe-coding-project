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
})
