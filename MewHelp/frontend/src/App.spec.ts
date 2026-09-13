import { mount } from '@vue/test-utils'
import App from './App.vue'

it('renders the MewHelp customer-service title', () => {
  expect(mount(App).get('h1').text()).toContain('小喵')
})
