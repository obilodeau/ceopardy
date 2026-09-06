<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
// In online mode the viewer is the tab that makes noise, but browsers refuse
// to play audio until the tab has seen a user gesture. This asks the
// operator for that one click while they are setting up the screen share; it
// never comes back afterwards, so it stays off the crowd screen during play.
import { computed } from "vue";
import { useGameStore } from "@/stores/game";
import { useSound } from "@/composables/useSound";

const game = useGameStore();
const { audioUnlocked, unlock } = useSound();

// The host embeds a viewer in an iframe; that copy must stay silent, so it
// has nothing to unlock.
const inIframe = window.self !== window.top;

const visible = computed(
  () => game.onlineMode && !audioUnlocked.value && !inIframe,
);
</script>

<template>
  <Transition name="fade">
    <div
      v-if="visible"
      class="container-game container-absolute container-all enable-sound"
      @click="unlock"
    >
      <div class="big-container-overlay">
        <div class="black-box flex-pad">
          <div class="box-overlay">
            <div class="box-ceopardy box-question-viewer">
              <p>Click to enable sound</p>
              <p class="enable-sound-hint">
                Online mode: the buzzers play on this screen.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.enable-sound {
  cursor: pointer;
}
.enable-sound-hint {
  font-size: 0.5em;
}
</style>
