<script setup lang="ts">
defineProps<{
  hasGame: boolean;
  isFinished: boolean;
  isDebug: boolean;
  isLoading: boolean;
}>();

defineEmits<{
  create: [];
  step: [];
  run: [];
  refresh: [];
  logs: [];
  delete: [];
  toggleDebug: [];
}>();
</script>

<template>
  <section class="panel control-panel">
    <div class="panel-title">
      <span>Controls</span>
      <small>{{ isLoading ? "请求中..." : "Ready" }}</small>
    </div>
    <div class="control-grid">
      <button :disabled="isLoading" @click="$emit('create')">创建新游戏</button>
      <button :disabled="!hasGame || isFinished || isLoading" @click="$emit('step')">执行下一步</button>
      <button :disabled="!hasGame || isFinished || isLoading" @click="$emit('run')">自动跑完整局</button>
      <button :disabled="!hasGame || isLoading" @click="$emit('refresh')">刷新状态</button>
      <button :disabled="!hasGame || isLoading" @click="$emit('logs')">获取日志</button>
      <button class="danger" :disabled="!hasGame || isLoading" @click="$emit('delete')">删除当前游戏</button>
      <button class="toggle" :disabled="isLoading" @click="$emit('toggleDebug')">
        {{ isDebug ? "关闭上帝视角" : "开启上帝视角" }}
      </button>
    </div>
  </section>
</template>
