<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup>
import { onBeforeMount } from "vue";
import { useGameStore } from "@/stores/game";

const game = useGameStore();

// Bootstrap the global game state as soon as the app mounts.
// Individual views (start/host/viewer) can still call `refresh()` when needed.
onBeforeMount(async () => {
  await game.refresh();
  game.connectSocket();
});
</script>

<template>
  <router-view />
</template>
