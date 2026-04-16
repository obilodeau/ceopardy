<script setup>
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'

const emit = defineEmits(['select'])
const game = useGameStore()

const rowHeight = computed(
  () => `${Math.floor(100 / game.config.QUESTIONS_PER_CATEGORY)}%`,
)

// Accent colours used in the little answer pills next to each question.
const ACCENTS = ['#d53405', '#d56c05', '#d5c105', '#05a5d5', '#8605d5']

function qid(col, row) {
  return `c${col}q${row}`
}
function isSelected(col, row) {
  return game.activeQuestionId === qid(col, row)
}
function isAnswered(col, row) {
  return game.questionAnswered(qid(col, row))
}
function teamScore(col, row, tid) {
  return game.questions[qid(col, row)]?.team_scores?.[tid] ?? ''
}
function teamAccent(i) {
  return ACCENTS[i % ACCENTS.length]
}
function onClick(col, row) {
  emit('select', qid(col, row))
}
</script>

<template>
  <div class="container-top container-all container-light">
    <!-- Categories row -->
    <div class="container-categories-host">
      <div class="black-box flex-small-pad">
        <div
          class="row-ceopardy flex-vertical-small-pad"
          style="height: 100%"
        >
          <div
            v-for="(name, idx) in game.categories"
            :key="idx"
            class="col-ceopardy flex-horizontal-small-pad"
          >
            <div :id="`c${idx + 1}`" class="box-ceopardy box-category-host">
              <p>{{ name }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="container-separator-h" />

    <!-- Questions grid -->
    <div class="container-questions-host">
      <div class="black-box flex-small-pad">
        <div
          v-for="row in game.config.QUESTIONS_PER_CATEGORY"
          :key="row"
          class="row-ceopardy flex-vertical-small-pad"
          :style="{ height: rowHeight }"
        >
          <div
            v-for="col in game.config.CATEGORIES_PER_GAME"
            :key="col"
            class="col-ceopardy flex-horizontal-small-pad"
          >
            <div
              :id="qid(col, row)"
              class="box-ceopardy box-question-host"
              :class="{
                'box-selected': isSelected(col, row),
                'box-answered': isAnswered(col, row),
              }"
              @click="onClick(col, row)"
            >
              <div class="box-question-left">
                <div
                  v-for="(team, i) in game.teams"
                  :key="team.tid"
                  class="box-question-status"
                  :style="{
                    backgroundColor:
                      teamScore(col, row, team.tid) !== ''
                        ? teamAccent(i)
                        : '',
                  }"
                >
                  <span>{{ teamScore(col, row, team.tid) }}</span>
                </div>
              </div>
              <div class="box-question-right">
                <p>${{ row * game.config.SCORE_TICK }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
