<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { onBeforeMount, onBeforeUnmount, watch } from "vue";
import { useGameStore } from "@/stores/game";
import { useSound } from "@/composables/useSound";

const game = useGameStore();
const { startThinking, stopThinking } = useSound();

// Bootstrap the global game state as soon as the app mounts.
// Individual views (start/host/viewer) can still call `refresh()` when needed.
onBeforeMount(async () => {
  await game.refresh();
  game.connectSocket();
});

// The waiting music is the one sound with duration, so it follows server
// state rather than an event. Watching it here means a client that joins or
// reloads in the middle of a break picks the music up too. useSound() itself
// decides whether this particular window is the one that should be heard.
watch(
  () => game.isThinking,
  (playing) => {
    if (playing) startThinking();
    else stopThinking();
  },
  { immediate: true },
);

// Never leave music playing behind us.
onBeforeUnmount(stopThinking);
</script>

<template>
  <router-view />
</template>
