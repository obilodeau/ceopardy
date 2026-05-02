<script setup>
import { ref } from "vue";

const props = defineProps({
  buzzersLocked: { type: Boolean, default: true },
});
const emit = defineEmits([
  "roulette",
  "timeout",
  "thinking",
  "toggle-buzzers",
  "submit",
  "finish",
]);

const spinning = ref(false);
function hoverSpinner(state) {
  spinning.value = state;
}
</script>

<template>
  <div class="container-bottom-left">
    <div class="black-box flex-small-pad">
      <div class="box-fake-overlay">
        <div class="box-ceopardy">
          <div class="container-controls form-color">
            <div
              class="form-icon form-click"
              title="Random team pick"
              @click="emit('roulette')"
              @mouseenter="hoverSpinner(true)"
              @mouseleave="hoverSpinner(false)"
            >
              <i
                class="fa-solid fa-arrows-spin fa-2x fa-fw"
                :class="{ 'fa-spin': spinning }"
              />
            </div>
            <div
              class="form-icon form-click"
              title="Timeout sound"
              @click="emit('timeout')"
            >
              <i class="fa-regular fa-clock fa-2x" />
            </div>
            <div
              class="form-icon form-click"
              title="Thinking music"
              @click="emit('thinking')"
            >
              <i class="fa-solid fa-music fa-2x" />
            </div>
            <div
              class="form-icon form-click"
              title="Lock / unlock buzzers"
              @click="emit('toggle-buzzers')"
            >
              <i
                class="fa-solid fa-2x fa-fw"
                :class="props.buzzersLocked ? 'fa-lock' : 'fa-lock-open'"
              />
            </div>
            <div
              class="form-icon form-click"
              title="Submit score"
              @click="emit('submit')"
            >
              <i class="fa-regular fa-square-check fa-2x" />
            </div>
            <div
              class="form-icon form-click"
              title="Finish the game"
              @click="emit('finish')"
            >
              <i class="fa-solid fa-right-from-bracket fa-2x" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
