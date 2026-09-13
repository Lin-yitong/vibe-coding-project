<script setup lang="ts">
import type { ChatSession } from '../types/chat'

defineProps<{
  sessions: ChatSession[]
  activeSessionId: string | null
  open: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  new: []
  close: []
}>()
</script>

<template>
  <aside v-if="open" class="session-sidebar">
    <div class="session-sidebar__header">
      <h2>会话记录</h2>
      <button data-action="close-sidebar" class="session-sidebar__close" type="button" aria-label="关闭会话列表" @click="emit('close')">
        ×
      </button>
    </div>

    <button data-action="new-session" class="session-sidebar__new" type="button" @click="emit('new')">
      ＋ 新对话
    </button>

    <nav aria-label="历史会话">
      <ul class="session-sidebar__list">
        <li v-for="session in sessions" :key="session.id">
          <button
            :data-session-id="session.id"
            class="session-sidebar__session"
            :class="{ 'session-sidebar__session--active': session.id === activeSessionId }"
            type="button"
            :aria-current="session.id === activeSessionId ? 'page' : undefined"
            @click="emit('select', session.id)"
          >
            <span class="session-sidebar__title">{{ session.title }}</span>
            <span class="session-sidebar__preview">{{ session.preview || '开始一段新对话' }}</span>
          </button>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<style scoped>
.session-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
  padding: 1rem;
  color: #2d1b35;
  background: #fff4dc;
  border-right: 3px solid #2d1b35;
}

.session-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.session-sidebar__header h2 {
  margin: 0;
  font-size: 1rem;
}

.session-sidebar__close,
.session-sidebar__new,
.session-sidebar__session {
  font: inherit;
  color: inherit;
  border: 2px solid #2d1b35;
  cursor: pointer;
}

.session-sidebar__close {
  width: 2rem;
  height: 2rem;
  background: #ffe7b6;
}

.session-sidebar__new {
  padding: 0.65rem 0.75rem;
  text-align: left;
  background: #ffb45b;
  box-shadow: 3px 3px 0 #2d1b35;
}

.session-sidebar__list {
  display: grid;
  gap: 0.6rem;
  padding: 0;
  margin: 0;
  list-style: none;
}

.session-sidebar__session {
  display: grid;
  width: 100%;
  gap: 0.25rem;
  padding: 0.7rem;
  text-align: left;
  background: #fffdfa;
}

.session-sidebar__session--active {
  background: #ffe0ad;
  box-shadow: 3px 3px 0 #2d1b35;
}

.session-sidebar__title {
  font-weight: 700;
}

.session-sidebar__preview {
  overflow: hidden;
  color: #6b536d;
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
