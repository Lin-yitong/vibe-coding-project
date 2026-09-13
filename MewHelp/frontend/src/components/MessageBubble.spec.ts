import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MessageBubble from './MessageBubble.vue'
import type { ChatMessage } from '../types/chat'

const assistant: ChatMessage = {
  id: 'assistant-1',
  role: 'assistant',
  content: '您好，请提供订单号。',
  status: 'complete',
}

describe('MessageBubble', () => {
  it('shows only assistant content, never a tool badge', () => {
    const wrapper = mount(MessageBubble, { props: { message: assistant } })

    expect(wrapper.text()).toContain('您好，请提供订单号。')
    expect(wrapper.text()).not.toContain('调用')
  })

  it('shows a streaming cursor only while the response is streaming', () => {
    const streaming = mount(MessageBubble, {
      props: { message: { ...assistant, status: 'streaming' } },
    })
    const complete = mount(MessageBubble, { props: { message: assistant } })

    expect(streaming.find('[data-streaming-cursor]').exists()).toBe(true)
    expect(complete.find('[data-streaming-cursor]').exists()).toBe(false)
  })

  it('uses a semantic label for the message author', () => {
    const userMessage: ChatMessage = {
      id: 'user-1',
      role: 'user',
      content: '我要退款',
      status: 'complete',
    }

    expect(mount(MessageBubble, { props: { message: userMessage } }).get('[aria-label]').attributes('aria-label')).toBe(
      '用户消息',
    )
    expect(mount(MessageBubble, { props: { message: assistant } }).get('[aria-label]').attributes('aria-label')).toBe(
      '客服消息',
    )
  })
})
