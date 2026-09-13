<script setup lang="ts">
const emit = defineEmits<{
  new: []
  toggleSessions: []
}>()
</script>

<template>
  <header class="chat-header">
    <button class="chat-header__sessions" type="button" aria-label="打开会话列表" @click="emit('toggleSessions')">
      会话
    </button>
    <div class="chat-header__brand">
      <span class="chat-header__cat" aria-hidden="true"><i></i></span>
      <div>
        <p class="chat-header__name">小喵 · 智能客服</p>
        <p class="chat-header__status"><span aria-hidden="true"></span>ONLINE</p>
      </div>
    </div>
    <button class="chat-header__new" type="button" @click="emit('new')">＋ 新对话</button>
  </header>
</template>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem 1rem;
  color: #2d1b35;
  background: #ff9b4a;
  border-bottom: 3px solid #2d1b35;
}

.chat-header__brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-right: auto;
}

.chat-header__cat {
  position: relative;
  display: block;
  width: 2rem;
  height: 1.7rem;
  background: #fff4dc;
  border: 2px solid #2d1b35;
}

.chat-header__cat::before,
.chat-header__cat::after {
  position: absolute;
  top: -0.55rem;
  width: 0.75rem;
  height: 0.75rem;
  content: '';
  background: #fff4dc;
  border: 2px solid #2d1b35;
}

.chat-header__cat::before {
  left: -0.08rem;
  transform: skewY(35deg);
}

.chat-header__cat::after {
  right: -0.08rem;
  transform: skewY(-35deg);
}

.chat-header__cat i,
.chat-header__cat i::before,
.chat-header__cat i::after {
  position: absolute;
  display: block;
  width: 0.18rem;
  height: 0.18rem;
  content: '';
  background: #2d1b35;
}

.chat-header__cat i {
  top: 0.65rem;
  left: 0.88rem;
}

.chat-header__cat i::before {
  top: -0.25rem;
  left: -0.45rem;
}

.chat-header__cat i::after {
  top: -0.25rem;
  left: 0.45rem;
}

.chat-header__name,
.chat-header__status {
  margin: 0;
}

.chat-header__name {
  font-weight: 800;
}

.chat-header__status {
  font-size: 0.68rem;
  letter-spacing: 0.08em;
}

.chat-header__status span {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  margin-right: 0.25rem;
  background: #3ec66a;
  border: 1px solid #2d1b35;
}

.chat-header__sessions,
.chat-header__new {
  padding: 0.45rem 0.65rem;
  font: inherit;
  color: inherit;
  background: #fff4dc;
  border: 2px solid #2d1b35;
  box-shadow: 2px 2px 0 #2d1b35;
  cursor: pointer;
}

.chat-header__sessions {
  display: none;
}

@media (max-width: 767px) {
  .chat-header__sessions {
    display: block;
  }
}
</style>
