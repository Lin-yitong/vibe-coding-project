<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '../types/chat'

const props = defineProps<{
  message: ChatMessage
}>()

const authorLabel = computed(() => (props.message.role === 'user' ? '用户消息' : '客服消息'))
</script>

<template>
  <article class="message-bubble" :class="`message-bubble--${message.role}`" :aria-label="authorLabel">
    <p>{{ message.content }}</p>
    <span v-if="message.status === 'streaming'" data-streaming-cursor class="message-bubble__cursor" aria-label="正在输入"></span>
  </article>
</template>

<style scoped>
.message-bubble {
  width: fit-content;
  max-width: min(80%, 42rem);
  padding: 0.75rem 0.9rem;
  border: 2px solid #2d1b35;
  box-shadow: 3px 3px 0 #2d1b35;
}

.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-bubble--user {
  align-self: end;
  color: #2d1b35;
  background: #ffb45b;
}

.message-bubble--assistant {
  align-self: start;
  background: #fffdfa;
}

.message-bubble__cursor {
  display: inline-block;
  width: 0.55rem;
  height: 1em;
  margin-left: 0.25rem;
  vertical-align: -0.15em;
  background: #ff8c45;
  animation: cursor-blink 0.8s steps(2, start) infinite;
}

@keyframes cursor-blink {
  50% { opacity: 0; }
}
</style>
