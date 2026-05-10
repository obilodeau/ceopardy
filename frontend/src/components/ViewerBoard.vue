<script setup>
import { computed } from "vue";
import { useGameStore } from "@/stores/game";
import DailyDoubleAnimation from "@/components/DailyDoubleAnimation.vue";

const game = useGameStore();

const rowHeight = computed(
  () => `${Math.floor(100 / game.config.QUESTIONS_PER_CATEGORY)}%`,
);

const showCategoriesRow = computed(
  () => !game.activeQuestionId && !game.isDailyDouble,
);
const activeCategory = computed(() => game.active_question?.category ?? "");

function qid(col, row) {
  return `c${col}q${row}`;
}

function isAnswered(col, row) {
  return game.questionAnswered(qid(col, row));
}

function questionLabel(row) {
  return `$${row * game.config.SCORE_TICK}`;
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
        <!-- DD overlay stays inside the black border and persists while DD is active. -->
        <DailyDoubleAnimation
          v-if="game.isDailyDouble"
          :key="game.dailydoubleTrigger"
        />
      </div>
    </div>

    <div class="container-separator-h" />

    <!-- Team result cards -->
    <div class="container-results">
      <div
        v-for="(team, idx) in game.teams"
        :key="team.tid"
        class="container-team"
      >
        <div
          :id="team.tid"
          class="black-box flex-pad"
          :class="{ 'team-selected': game.selectedTeam === team.tid }"
          style="width: 80%; max-width: 250px; margin: auto"
        >
          <div class="col-player flex-horizontal-pad">
            <div class="row-player flex-vertical-pad" style="height: 30%">
              <div :id="`${team.tid}-score`" class="box-ceopardy box-score">
                <p>${{ team.score }}</p>
              </div>
            </div>
            <div class="row-player flex-vertical-pad" style="height: 70%">
              <div
                :id="`${team.tid}-name`"
                class="box-ceopardy box-team"
                :class="`team${idx + 1}-font`"
              >
                <p>{{ team.name }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
