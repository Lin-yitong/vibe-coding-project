import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SessionSidebar from './SessionSidebar.vue'
import type { ChatSession } from '../types/chat'

const sessions: ChatSession[] = [
  { id: 'order-help', title: '订单咨询', preview: '我的订单还没发货', messages: [] },
  { id: 'refund-help', title: '退款申请', preview: '想申请退款', messages: [] },
]

describe('SessionSidebar', () => {
  it('marks the active session and emits its id when selected', async () => {
    const wrapper = mount(SessionSidebar, {
      props: { sessions, activeSessionId: 'refund-help', open: true },
    })

    expect(wrapper.get('[aria-current="page"]').text()).toContain('退款申请')

    await wrapper.get('[data-session-id="order-help"]').trigger('click')

    expect(wrapper.emitted('select')?.[0]).toEqual(['order-help'])
  })

  it('emits new and close from the sidebar controls', async () => {
    const wrapper = mount(SessionSidebar, {
      props: { sessions, activeSessionId: 'order-help', open: true },
    })

    await wrapper.get('[data-action="new-session"]').trigger('click')
    await wrapper.get('[data-action="close-sidebar"]').trigger('click')

    expect(wrapper.emitted('new')).toHaveLength(1)
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
