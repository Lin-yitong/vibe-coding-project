<script setup lang="ts">
import LogPanel from "./LogPanel.vue";

defineProps<{
  logs: string[];
  visible: boolean;
}>();
</script>

<template>
  <LogPanel v-if="visible" title="God View Logs" :logs="logs" tone="debug" />
</template>
