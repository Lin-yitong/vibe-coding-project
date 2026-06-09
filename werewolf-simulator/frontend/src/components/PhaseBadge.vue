<script setup lang="ts">
import type { GamePhase } from "../types/game";

defineProps<{
  phase?: GamePhase;
}>();

const phaseLabels: Record<GamePhase, string> = {
  NIGHT_WOLF: "狼人行动阶段",
  NIGHT_SEER: "预言家查验阶段",
  NIGHT_WITCH: "女巫行动阶段",
  DAY_ANNOUNCEMENT: "公布昨夜死亡情况",
  DAY_SPEECH: "白天发言阶段",
  DAY_VOTE: "投票阶段",
  EXILE: "放逐结算阶段",
  GAME_OVER: "游戏结束",
};

function phaseLabel(phase?: GamePhase) {
  return phase ? phaseLabels[phase] : "等待创建游戏";
}
</script>

<template>
  <div class="phase-badge" :class="{ 'phase-badge--over': phase === 'GAME_OVER' }">
    <span class="phase-badge__code">{{ phase || "NO_GAME" }}</span>
    <span class="phase-badge__label">{{ phaseLabel(phase) }}</span>
  </div>
</template>
