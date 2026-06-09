<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  createGame,
  deleteGame,
  getGame,
  getHealth,
  getLogs,
  runGame,
  stepGame,
} from "./api/gameApi";
import ControlPanel from "./components/ControlPanel.vue";
import DebugPanel from "./components/DebugPanel.vue";
import GameStatusCard from "./components/GameStatusCard.vue";
import Header from "./components/Header.vue";
import LogPanel from "./components/LogPanel.vue";
import PlayerList from "./components/PlayerList.vue";
import type { GameState } from "./types/game";

const game = ref<GameState | null>(null);
const debugMode = ref(false);
const loading = ref(false);
const error = ref("");
const backendStatus = ref("checking");
const lastAction = ref("等待操作");

const isFinished = computed(() => game.value?.phase === "GAME_OVER");
const debugLogs = computed(() => (debugMode.value ? game.value?.debug_logs || [] : []));

async function withLoading(label: string, action: () => Promise<void>) {
  loading.value = true;
  error.value = "";
  lastAction.value = label;
  try {
    await action();
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
  } finally {
    loading.value = false;
  }
}

async function checkHealth() {
  try {
    const health = await getHealth();
    backendStatus.value = health.status;
  } catch (err) {
    backendStatus.value = "offline";
    error.value = err instanceof Error ? err.message : String(err);
  }
}

async function handleCreate() {
  await withLoading("创建新游戏", async () => {
    game.value = await createGame();
    if (debugMode.value) {
      game.value = await getGame(game.value.game_id, true);
    }
  });
}

async function handleStep() {
  if (!game.value) return;
  await withLoading("执行下一步", async () => {
    await stepGame(game.value!.game_id);
    game.value = await getGame(game.value!.game_id, debugMode.value);
  });
}

async function handleRun() {
  if (!game.value) return;
  await withLoading("自动跑完整局", async () => {
    await runGame(game.value!.game_id);
    game.value = await getGame(game.value!.game_id, debugMode.value);
  });
}

async function handleRefresh() {
  if (!game.value) return;
  await withLoading("刷新状态", async () => {
    game.value = await getGame(game.value!.game_id, debugMode.value);
  });
}

async function handleLogs() {
  if (!game.value) return;
  await withLoading("获取日志", async () => {
    const logs = await getLogs(game.value!.game_id, debugMode.value);
    game.value = {
      ...game.value!,
      public_logs: logs.public_logs,
      debug_logs: logs.debug_logs,
    };
  });
}

async function handleDelete() {
  if (!game.value) return;
  await withLoading("删除当前游戏", async () => {
    await deleteGame(game.value!.game_id);
    game.value = null;
    lastAction.value = "当前游戏已删除";
  });
}

async function handleToggleDebug() {
  debugMode.value = !debugMode.value;
  if (!game.value) return;
  await withLoading(debugMode.value ? "开启 Debug" : "关闭 Debug", async () => {
    game.value = await getGame(game.value!.game_id, debugMode.value);
  });
}

onMounted(() => {
  void checkHealth();
});
</script>

<template>
  <div class="shell">
    <Header :game-id="game?.game_id" :backend-status="backendStatus" />

    <main class="layout">
      <section class="left-column">
        <ControlPanel
          :has-game="Boolean(game)"
          :is-finished="isFinished"
          :is-debug="debugMode"
          :is-loading="loading"
          @create="handleCreate"
          @step="handleStep"
          @run="handleRun"
          @refresh="handleRefresh"
          @logs="handleLogs"
          @delete="handleDelete"
          @toggle-debug="handleToggleDebug"
        />

        <GameStatusCard :game="game" :debug="debugMode" />

        <section class="panel phase-panel">
          <div class="panel-title">
            <span>Phase Notes</span>
            <small>{{ lastAction }}</small>
          </div>
          <p v-if="!game">创建一局游戏后，这里会展示当前阶段和对局状态。开启上帝视角后可以看到隐藏身份和夜晚行动细节。</p>
          <p v-else-if="game.phase === 'NIGHT_WOLF'">狼人行动阶段：后端调用 Agent 选择夜晚击杀目标，公开日志不会泄露夜晚目标。</p>
          <p v-else-if="game.phase === 'NIGHT_SEER'">预言家查验阶段：预言家选择一名存活玩家查验，结果只进入调试信息。</p>
          <p v-else-if="game.phase === 'NIGHT_WITCH'">女巫行动阶段：女巫可选择救人或毒人，每瓶药只能使用一次。</p>
          <p v-else-if="game.phase === 'DAY_ANNOUNCEMENT'">公布昨夜死亡情况：公开日志会展示夜晚死亡结果。</p>
          <p v-else-if="game.phase === 'DAY_SPEECH'">白天发言阶段：存活玩家依次发言，死亡玩家不会发言。</p>
          <p v-else-if="game.phase === 'DAY_VOTE'">投票阶段：存活玩家投票，所有投票仍由规则校验。</p>
          <p v-else-if="game.phase === 'EXILE'">放逐结算阶段：最高票玩家出局，平票则无人出局。</p>
          <p v-else>游戏结束：胜负结果已产生，可创建新游戏继续测试。</p>
        </section>

        <div v-if="error" class="error-box">{{ error }}</div>
      </section>

      <section class="right-column">
        <PlayerList :players="game?.players || []" :debug="debugMode" />
        <div class="logs-grid">
          <LogPanel title="Public Logs" :logs="game?.public_logs || []" tone="public" />
          <DebugPanel :visible="debugMode" :logs="debugLogs" />
        </div>
      </section>
    </main>
  </div>
</template>
