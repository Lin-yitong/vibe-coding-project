<script setup lang="ts">
import type { GameState } from "../types/game";
import PhaseBadge from "./PhaseBadge.vue";

defineProps<{
  game: GameState | null;
  debug: boolean;
}>();
</script>

<template>
  <section class="panel status-panel">
    <div class="panel-title">
      <span>Game Status</span>
      <small>{{ debug ? "God View" : "Public View" }}</small>
    </div>
    <PhaseBadge :phase="game?.phase" />
    <div class="status-grid">
      <div>
        <span>game_id</span>
        <strong>{{ game?.game_id || "-" }}</strong>
      </div>
      <div>
        <span>day_number</span>
        <strong>{{ game?.day_number ?? "-" }}</strong>
      </div>
      <div>
        <span>winner</span>
        <strong>{{ game?.winner || "-" }}</strong>
      </div>
      <div>
        <span>is_finished</span>
        <strong>{{ game?.phase === "GAME_OVER" ? "true" : "false" }}</strong>
      </div>
    </div>
  </section>
</template>
