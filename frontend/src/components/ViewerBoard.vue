<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { computed } from "vue";
import { useGameStore } from "@/stores/game";
import DailyDoubleAnimation from "@/components/DailyDoubleAnimation.vue";
import TeamRow from "@/components/TeamRow.vue";
import TeamRowDailyDouble from "@/components/TeamRowDailyDouble.vue";

const game = useGameStore();

const rowHeight = computed(
  () => `${Math.floor(100 / (game.config.QUESTIONS_PER_CATEGORY ?? 5))}%`,
);

const showCategoriesRow = computed(
  () => !game.activeQuestionId && !game.isDailyDouble,
);
const activeCategory = computed(() => game.active_question?.category ?? "");

function qid(col: number, row: number): string {
  return `c${col}q${row}`;
}

function isAnswered(col: number, row: number): boolean {
  return game.questionAnswered(qid(col, row));
}

function questionLabel(row: number): string {
  return `$${row * (game.config.SCORE_TICK ?? 100)}`;
}
</script>

<template>
  <div class="container-game container-all container-light">
    <!-- Categories / single category overlay -->
    <div class="container-categories-viewer">
      <div class="black-box flex-pad">
        <div
          class="row-ceopardy flex-vertical-pad"
          style="height: 100%"
          :class="{ 'no-display': !showCategoriesRow }"
        >
          <div
            v-for="(name, idx) in game.categories"
            :key="idx"
            class="col-ceopardy flex-horizontal-pad"
          >
            <div :id="`c${idx + 1}`" class="box-ceopardy box-category-viewer">
              <p>{{ name }}</p>
            </div>
          </div>
        </div>

        <div
          class="row-ceopardy flex-vertical-pad"
          style="height: 100%"
          :class="{ 'no-display': showCategoriesRow }"
        >
          <div class="col-ceopardy flex-horizontal-pad">
            <div class="box-ceopardy box-category-viewer">
              <p>{{ activeCategory }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="container-separator-h" />

    <!-- Dollar value grid -->
    <div class="container-questions-viewer">
      <div class="black-box flex-pad">
        <div
          v-for="row in game.config.QUESTIONS_PER_CATEGORY"
          :key="row"
          class="row-ceopardy flex-vertical-pad"
          :style="{ height: rowHeight }"
        >
          <div
            v-for="col in game.config.CATEGORIES_PER_GAME"
            :key="col"
            class="col-ceopardy flex-horizontal-pad"
          >
            <div
              :id="qid(col, row)"
              class="box-ceopardy box-question-viewer"
              role="button"
            >
              <p :class="{ answered: isAnswered(col, row) }">
                {{ questionLabel(row) }}
              </p>
            </div>
          </div>
        </div>
        <!-- DD overlay stays inside the black border until the clue is revealed. -->
        <DailyDoubleAnimation
          v-if="game.isDailyDouble && !game.isDailyDoubleRevealed"
          :key="game.dailydoubleTrigger"
        />
      </div>
    </div>

    <div class="container-separator-h" />

    <!-- Team result cards: normal row vs DD layout, swapped with a fade. -->
    <Transition name="dd-rowfade" mode="out-in">
      <TeamRowDailyDouble v-if="game.isDailyDouble" key="dd" />
      <TeamRow v-else key="normal" />
    </Transition>
  </div>
</template>
