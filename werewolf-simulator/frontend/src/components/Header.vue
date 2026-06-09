<script setup lang="ts">
import { API_BASE_URL } from "../api/client";

defineProps<{
  gameId?: string;
  backendStatus: string;
}>();
</script>

<template>
  <header class="app-header">
    <div>
      <p class="eyebrow">LLM Werewolf Debug Console</p>
      <h1>AI Werewolf Simulator</h1>
    </div>
    <div class="header-meta">
      <div>
        <span>Backend</span>
        <strong>{{ API_BASE_URL }}</strong>
      </div>
      <div>
        <span>Status</span>
        <strong>{{ backendStatus }}</strong>
      </div>
      <div>
        <span>Game ID</span>
        <strong>{{ gameId || "未创建" }}</strong>
      </div>
    </div>
  </header>
</template>
