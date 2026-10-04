<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '../types/chat'

const props = defineProps<{
  message: ChatMessage
}>()

const authorLabel = computed(() => (props.message.role === 'user' ? '用户消息' : '客服消息'))
const toolNames = computed(() => props.message.toolNames ?? [])
</script>

<template>
  <article class="message-bubble" :class="`message-bubble--${message.role}`" :aria-label="authorLabel">
    <div
      v-if="message.role === 'assistant' && toolNames.length > 0"
      class="message-bubble__tools"
      aria-label="已使用工具"
    >
      <span v-for="name in toolNames" :key="name" class="message-bubble__tool">
        <span class="message-bubble__tool-icon" aria-hidden="true">🔧</span>
        <span>调用了</span>
        <code>{{ name }}</code>
      </span>
    </div>
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

.message-bubble__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}

.message-bubble__tool {
  display: inline-flex;
  gap: 0.35rem;
  align-items: center;
  padding: 0.3rem 0.65rem;
  color: #817b78;
  font-size: 0.75rem;
  line-height: 1;
  background: #faf8f2;
  border: 1px dashed #aaa39b;
  border-radius: 999px;
}

.message-bubble__tool code {
  color: inherit;
  font: inherit;
}

.message-bubble__tool-icon {
  font-size: 0.9rem;
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
