import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatComposer from './ChatComposer.vue'

describe('ChatComposer', () => {
  it('sends on Enter but keeps a newline on Shift+Enter', async () => {
    const wrapper = mount(ChatComposer)
    const textarea = wrapper.get('textarea')

    await textarea.setValue('退款申请')
    await textarea.trigger('keydown.enter')

    expect(wrapper.emitted('send')?.[0]).toEqual(['退款申请'])

    await textarea.setValue('退款申请\n补充订单号')
    await textarea.trigger('keydown.enter', { shiftKey: true })

    expect(wrapper.emitted('send')).toHaveLength(1)
    expect((textarea.element as HTMLTextAreaElement).value).toBe('退款申请\n补充订单号')
  })

  it('trims messages and never sends blank text', async () => {
    const wrapper = mount(ChatComposer)
    const textarea = wrapper.get('textarea')

    await textarea.setValue('  我想退款  ')
    await textarea.trigger('keydown.enter')
    await textarea.setValue('  \n  ')
    await textarea.trigger('keydown.enter')

    expect(wrapper.emitted('send')).toEqual([['我想退款']])
  })

  it('disables sending while disabled or busy', () => {
    const disabled = mount(ChatComposer, { props: { disabled: true } })
    const busy = mount(ChatComposer, { props: { busy: true } })

    expect(disabled.get('textarea').attributes('disabled')).toBeDefined()
    expect(disabled.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(busy.get('textarea').attributes('disabled')).toBeDefined()
    expect(busy.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(busy.text()).toContain('客服正在处理')
  })
})
