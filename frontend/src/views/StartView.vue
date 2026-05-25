<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api";
import { useGameStore } from "@/stores/game";

const router = useRouter();
const game = useGameStore();

const roundfiles = ref([]);
const showRoundfiles = ref(false);
const mustInit = ref(true);

onMounted(async () => {
  roundfiles.value = await api.roundfiles();
  // If a game has already been played the server lets us resume it.
  mustInit.value = !game.initialized
    ? true
    : game.game_state === "uninitialized";
});

async function startNew(filename) {
  await api.init({ action: "new", name: filename });
  await game.refresh();
  router.push({ name: "host" });
}

async function resume() {
  await api.init({ action: "resume" });
  await game.refresh();
  router.push({ name: "host" });
}
</script>

<template>
  <div class="start-container container-light">
    <div style="flex-grow: 1" />
    <div class="start-title">Ceopardy!</div>

    <div class="start-menu">
      <i class="fa-solid fa-arrow-right animate-horizontal-right" />
      <a @click="showRoundfiles = !showRoundfiles">New Game</a>
      <i class="fa-solid fa-arrow-left animate-horizontal-left" />
    </div>

    <div v-if="showRoundfiles" class="start-menu">
      <template v-for="(file, i) in roundfiles" :key="file">
        <span v-if="i > 0" style="color: #d5c19c"> · </span>
        <a @click="startNew(file)">{{ file }}</a>
      </template>
      <div v-if="roundfiles.length === 0" style="margin-top: 10px">
        No round files found in <code>data/</code>.
      </div>
    </div>

    <div v-if="!mustInit && game.game_state === 'finished'" class="start-menu">
      <i class="fa-solid fa-rotate-left" />
      <a @click="resume">Resume Last Game</a>
    </div>

    <div style="flex-grow: 1" />
  </div>
</template>
