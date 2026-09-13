<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    disabled?: boolean
    busy?: boolean
  }>(),
  {
    disabled: false,
    busy: false,
  },
)

const emit = defineEmits<{
  send: [message: string]
}>()

const draft = ref('')
const isDisabled = computed(() => props.disabled || props.busy)

function submit(): void {
  const message = draft.value.trim()
  if (!message || isDisabled.value) {
    return
  }

  emit('send', message)
  draft.value = ''
}
</script>

<template>
  <form class="chat-composer" @submit.prevent="submit">
    <label class="chat-composer__label" for="chat-message">输入您的问题</label>
    <textarea
      id="chat-message"
      v-model="draft"
      class="chat-composer__input"
      rows="3"
      placeholder="输入消息，Enter 发送，Shift+Enter 换行"
      :disabled="isDisabled"
      @keydown.enter.exact.prevent="submit"
    ></textarea>
    <p v-if="busy" class="chat-composer__busy" role="status">客服正在处理…</p>
    <button class="chat-composer__send" type="submit" :disabled="isDisabled">发送</button>
  </form>
</template>

<style scoped>
.chat-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.55rem;
  padding: 1rem;
  background: #fff4dc;
  border-top: 3px solid #2d1b35;
}

.chat-composer__label,
.chat-composer__busy {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 0.8rem;
}

.chat-composer__busy {
  color: #82536e;
}

.chat-composer__input {
  width: 100%;
  min-height: 3.5rem;
  box-sizing: border-box;
  padding: 0.6rem;
  font: inherit;
  resize: vertical;
  background: #fffdfa;
  border: 2px solid #2d1b35;
}

.chat-composer__send {
  align-self: end;
  padding: 0.6rem 0.85rem;
  font: inherit;
  color: #2d1b35;
  background: #ffb45b;
  border: 2px solid #2d1b35;
  box-shadow: 3px 3px 0 #2d1b35;
  cursor: pointer;
}

.chat-composer__send:disabled,
.chat-composer__input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
