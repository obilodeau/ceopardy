<script setup>
// Full-screen overlay used for "Game is starting", "Break", etc.
// HTML comes pre-rendered from the server (already sanitized upstream).
import { computed } from "vue";
import { useGameStore } from "@/stores/game";

const game = useGameStore();
const visible = computed(() => !!game.bigOverlayHtml);
</script>

<template>
  <Transition name="fade">
    <div v-if="visible" class="container-game container-absolute container-all">
      <div class="big-container-overlay">
        <div class="black-box flex-pad">
          <div class="box-overlay">
            <div
              class="box-ceopardy box-question-viewer"
              v-html="game.bigOverlayHtml"
            />
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>
