<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { streamChat } from './api/chatClient'
import ChatComposer from './components/ChatComposer.vue'
import ChatHeader from './components/ChatHeader.vue'
import MessageBubble from './components/MessageBubble.vue'
import SessionSidebar from './components/SessionSidebar.vue'
import { createSessionId, useChatSessions } from './composables/useChatSessions'
import type { ChatMessage, ChatSession } from './types/chat'

const { activeSessionId, activateSession, createSession, currentSession, sessions } = useChatSessions()
const isBusy = ref(false)
const sidebarOpen = ref(true)
const messageList = ref<HTMLElement | null>(null)
const messages = computed(() => currentSession.value?.messages ?? [])

function isNarrowScreen(): boolean {
  return window.matchMedia?.('(max-width: 767px)').matches ?? false
}

async function scrollToLatestMessage(): Promise<void> {
  await nextTick()
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}

function updateSessionSummary(session: ChatSession, message: string): void {
  if (session.title === '新对话') {
    session.title = message.slice(0, 18)
  }
  session.preview = message.slice(0, 36)
}

function createNewSession(): void {
  createSession()
  if (isNarrowScreen()) {
    sidebarOpen.value = false
  }
  void scrollToLatestMessage()
}

function selectSession(id: string): void {
  activateSession(id)
  if (isNarrowScreen()) {
    sidebarOpen.value = false
  }
  void scrollToLatestMessage()
}

async function sendMessage(content: string): Promise<void> {
  if (isBusy.value || !currentSession.value) {
    return
  }

  const session = currentSession.value
  const userMessage: ChatMessage = {
    id: createSessionId(),
    role: 'user',
    content,
    status: 'complete',
  }
  const streamingMessage: ChatMessage = {
    id: createSessionId(),
    role: 'assistant',
    content: '',
    status: 'streaming',
  }

  session.messages.push(userMessage, streamingMessage)
  const assistantMessage = session.messages[session.messages.length - 1]!
  updateSessionSummary(session, content)
  isBusy.value = true
  void scrollToLatestMessage()

  await streamChat(
    { sessionId: session.id, message: content },
    {
      onDelta(delta) {
        assistantMessage.content += delta
        session.preview = assistantMessage.content.slice(0, 36) || content.slice(0, 36)
        void scrollToLatestMessage()
      },
      onDone() {
        assistantMessage.status = 'complete'
        isBusy.value = false
        void scrollToLatestMessage()
      },
      onError(message) {
        assistantMessage.status = 'error'
        assistantMessage.content = assistantMessage.content
          ? `${assistantMessage.content}\n\n${message}`
          : message
        session.preview = assistantMessage.content.slice(0, 36)
        isBusy.value = false
        void scrollToLatestMessage()
      },
    },
  )
}
</script>

<template>
  <main class="mewhelp-app">
    <ChatHeader @new="createNewSession" @toggle-sessions="sidebarOpen = !sidebarOpen" />
    <div class="mewhelp-app__workspace">
      <SessionSidebar
        :sessions="sessions"
        :active-session-id="activeSessionId"
        :open="sidebarOpen"
        @new="createNewSession"
        @select="selectSession"
        @close="sidebarOpen = false"
      />

      <section class="mewhelp-app__chat" aria-label="客服对话">
        <div ref="messageList" class="mewhelp-app__messages" aria-live="polite">
          <p v-if="messages.length === 0" class="mewhelp-app__empty">告诉小喵您遇到的问题吧。</p>
          <MessageBubble v-for="message in messages" :key="message.id" :message="message" />
        </div>
        <ChatComposer :busy="isBusy" @send="sendMessage" />
      </section>
    </div>
  </main>
</template>
