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
      class="sound-blocked"
      role="alertdialog"
      aria-labelledby="sound-blocked-title"
      @click="unlock"
    >
      <div class="sound-blocked-panel">
        <p id="sound-blocked-title" class="sound-blocked-title">
          <span class="sound-blocked-icon" aria-hidden="true">&#9888;</span>
          Audio blocked
        </p>
        <p class="sound-blocked-body">
          This browser will not play sound until the page has been clicked.
        </p>
        <p class="sound-blocked-body sound-blocked-muted">
          Online mode is on, so the buzzers and the waiting music play on this
          screen rather than on the host's.
        </p>
        <button type="button" class="sound-blocked-action">
          Click anywhere to enable sound
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Deliberately not the Jeopardy chrome the other overlays use (blue box, gold
   embossed text): this is the app talking to the operator during setup, not a
   clue for the crowd, so it reads as a system notice — neutral dark panel,
   monospace, amber accent — and stays a small centered dialog instead of
   filling the board. */
.sound-blocked {
  position: fixed;
  inset: 0;
  /* Above the Daily Double animation (5000). The host's drawers (10000) are
     not on the viewer, so nothing else competes here. */
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5vmin;
  background-color: rgba(0, 0, 0, 0.72);
  cursor: pointer;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}

.sound-blocked-panel {
  width: 100%;
  max-width: 40rem;
  padding: clamp(1.1rem, 2.6vmin, 2rem);
  background-color: #16181d;
  border: 1px solid #383d47;
  border-top: 3px solid #f0b429;
  border-radius: 4px;
  box-shadow: 0 1.5rem 3rem rgba(0, 0, 0, 0.55);
}

.sound-blocked-title {
  margin: 0 0 0.9em;
  color: #f0b429;
  font-size: clamp(0.95rem, 1.7vmin, 1.3rem);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.sound-blocked-icon {
  /* U+26A0 lands small and thin in a monospace face; nudge it back up so the
     line reads as a warning rather than as stray punctuation. */
  margin-right: 0.5em;
  font-size: 1.25em;
  line-height: 1;
}

/* One step down from the title, not the 5vw-clue-then-0.5em-footnote jump
   that made the first version look like a mis-styled question box. */
.sound-blocked-body {
  margin: 0 0 0.8em;
  color: #d3d7de;
  font-size: clamp(0.85rem, 1.5vmin, 1.15rem);
  line-height: 1.6;
}
.sound-blocked-muted {
  color: #8f96a3;
}

/* A real button so the dialog is keyboard-reachable; the click bubbles to the
   overlay, which is what actually unlocks. */
.sound-blocked-action {
  margin-top: 0.6em;
  padding: 0.7em 1.1em;
  border: 1px solid #f0b429;
  border-radius: 3px;
  background-color: transparent;
  color: #f0b429;
  font-family: inherit;
  font-size: clamp(0.8rem, 1.35vmin, 1.05rem);
  letter-spacing: 0.04em;
  cursor: pointer;
}
.sound-blocked-action:hover,
.sound-blocked-action:focus-visible {
  background-color: #f0b429;
  color: #16181d;
}
</style>
