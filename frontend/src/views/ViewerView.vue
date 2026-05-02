<script setup>
// Crowd-facing UI. Listens to the store for state changes pushed from the
// server and renders the big Jeopardy board.
import { ref, watch } from "vue";
import ViewerBoard from "@/components/ViewerBoard.vue";
import QuestionOverlay from "@/components/QuestionOverlay.vue";
import BigOverlay from "@/components/BigOverlay.vue";
import DailyDoubleAnimation from "@/components/DailyDoubleAnimation.vue";
import { useGameStore } from "@/stores/game";

const game = useGameStore();

// Show the daily-double flip when the server fires the event. We watch the
// trigger counter, not `isDailyDouble`, so we won't replay the animation on
// reconnect if the game was already in DD mode.
const ddAnimating = ref(false);
watch(
  () => game.dailydoubleTrigger,
  () => {
    ddAnimating.value = true;
    playSound("dailydouble");
  },
);

const sounds = {
  dailydouble: "/static/sounds/daily-double.mp3",
  reveal: "/static/sounds/reveal.mp3",
};
function playSound(name) {
  try {
    const audio = new Audio(sounds[name]);
    audio.play().catch(() => {
      // Browsers may block auto-play until the user has interacted.
    });
  } catch {
    /* ignore */
  }
}
</script>

<template>
  <div>
    <ViewerBoard />
    <QuestionOverlay />
    <BigOverlay />
    <DailyDoubleAnimation v-if="ddAnimating" @done="ddAnimating = false" />
  </div>
</template>
