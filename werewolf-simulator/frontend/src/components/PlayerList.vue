<script setup lang="ts">
import type { Player } from "../types/game";

defineProps<{
  players: Player[];
  debug: boolean;
}>();
</script>

<template>
  <section class="panel players-panel">
    <div class="panel-title">
      <span>Players</span>
      <small>{{ players.length }}/6</small>
    </div>
    <div class="players-grid">
      <article v-for="player in players" :key="player.player_id" class="player-card" :class="{ dead: !player.is_alive }">
        <div class="player-card__top">
          <span class="seat">#{{ player.seat_number }}</span>
          <span class="alive" :class="{ off: !player.is_alive }">{{ player.is_alive ? "ALIVE" : "DEAD" }}</span>
        </div>
        <h3>{{ player.nickname }}</h3>
        <dl>
          <div>
            <dt>ID</dt>
            <dd>{{ player.player_id }}</dd>
          </div>
          <div>
            <dt>AI</dt>
            <dd>{{ player.is_ai ? "true" : "false" }}</dd>
          </div>
          <div v-if="debug && player.role">
            <dt>Role</dt>
            <dd class="role">{{ player.role }}</dd>
          </div>
        </dl>
      </article>
    </div>
  </section>
</template>
