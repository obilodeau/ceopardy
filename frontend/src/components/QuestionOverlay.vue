<script setup>
import { computed } from "vue";
import { useGameStore } from "@/stores/game";

const game = useGameStore();

const visible = computed(() => !!game.activeQuestionId && !game.isDailyDouble);
const html = computed(() => game.active_question?.text ?? "");
</script>

<template>
  <Transition name="fade">
    <div v-if="visible" class="container-game container-absolute container-all">
      <div class="container-question-viewer">
        <div class="black-box flex-pad">
          <div class="container-question row-ceopardy flex-vertical-pad">
            <div class="col-ceopardy flex-horizontal-pad">
              <div class="box-ceopardy box-question-viewer" v-html="html" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>
