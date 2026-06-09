<script setup lang="ts">
defineProps<{
  title: string;
  logs: string[];
  tone?: "public" | "debug";
}>();
</script>

<template>
  <section class="panel log-panel" :class="`log-panel--${tone || 'public'}`">
    <div class="panel-title">
      <span>{{ title }}</span>
      <small>{{ logs.length }} entries</small>
    </div>
    <ol class="log-list">
      <li v-for="(log, index) in logs" :key="`${index}-${log}`" :class="{ latest: index === logs.length - 1 }">
        <span>{{ String(index + 1).padStart(2, "0") }}</span>
        <p>{{ log }}</p>
      </li>
      <li v-if="logs.length === 0" class="empty-log">暂无日志</li>
    </ol>
  </section>
</template>
