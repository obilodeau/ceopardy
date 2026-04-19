<script setup>
import { computed } from 'vue'
import { useGameStore } from '@/stores/game'
import { api } from '@/api'

const props = defineProps({
  team: { type: Object, required: true },
  idx: { type: Number, required: true },
  answers: { type: Object, required: true },
})

const emit = defineEmits(['update:answers'])

const game = useGameStore()

const tid = computed(() => props.team.tid)
const dailydouble = computed(() => game.isDailyDouble)

const teamSelected = computed(() => game.selectedTeam === tid.value)

const disabled = computed(
  () => dailydouble.value && game.selectedTeam !== tid.value,
)

function updateAnswer(val) {
  const out = { ...props.answers, [tid.value]: val }
  emit('update:answers', out)
}
function updateDouble(val) {
  const key = `${tid.value}-dailydouble`
  emit('update:answers', { ...props.answers, [key]: val })
}
function updateWaiger(val) {
  const key = `${tid.value}-waiger-dailydouble`
  emit('update:answers', { ...props.answers, [key]: val })
}

function selectTeam() {
  api.selectTeam(tid.value)
}

const answerVal = computed(() => props.answers[tid.value] ?? 0)
const doubleVal = computed(
  () => props.answers[`${tid.value}-dailydouble`] ?? -1,
)
const waigerVal = computed(
  () => props.answers[`${tid.value}-waiger-dailydouble`] ?? game.dailydouble_range.max,
)

const teamFontClass = `team${props.idx + 1}-font`
</script>

<template>
  <div class="container-bottom-team" style="height: 100%">
    <div
      class="black-box flex-small-pad"
      :class="{
        'team-selected': teamSelected,
        disabled: disabled,
      }"
      style="width: 100%; margin: auto"
    >
      <div
        class="row-ceopardy col-ceopardy flex-small-pad"
        style="height: 100%"
      >
        <div class="box-ceopardy">
          <div class="box-team-side">
            <div
              class="box-answer-team form-color"
              style="display: flex; vertical-align: middle; margin: auto"
            >
              <div
                class="form-icon form-click"
                title="Give control to this team"
                @click="selectTeam"
              >
                <i class="fa-solid fa-crosshairs fa-2x" />
              </div>
            </div>
          </div>
          <div class="box-team-middle">
            <div class="box-ceopardy box-team-host" :class="teamFontClass">
              <p>{{ team.name }}</p>
            </div>

            <!-- Normal scoring -->
            <div
              v-if="!dailydouble"
              class="box-answer-range"
            >
              <input
                class="team-range"
                :name="tid"
                type="range"
                min="-1"
                max="1"
                step="1"
                :value="answerVal"
                @input="updateAnswer(Number($event.target.value))"
              />
              <div class="box-answer-range-label">
                <div><p>Bad</p></div>
                <div><p>No Answer</p></div>
                <div><p>Good</p></div>
              </div>
            </div>

            <!-- Daily double scoring -->
            <div v-else class="box-answer-range">
              <input
                class="team-range"
                :name="`${tid}-waiger-dailydouble`"
                type="range"
                :min="game.dailydouble_range.min"
                :max="game.dailydouble_range.max"
                step="1"
                :value="waigerVal"
                @input="updateWaiger(Number($event.target.value))"
              />
              <div class="box-answer-range-label">
                <div><p>Minimum</p></div>
                <div>
                  <p>{{ waigerVal }}</p>
                </div>
                <div><p>All-in!</p></div>
              </div>
              <input
                class="team-range"
                :name="`${tid}-answer-dailydouble`"
                type="range"
                min="-1"
                max="1"
                step="2"
                :value="doubleVal"
                @input="updateDouble(Number($event.target.value))"
              />
              <div class="box-answer-range-label">
                <div><p>Bad / No Answer</p></div>
                <div><p>Good</p></div>
              </div>
            </div>
          </div>
          <div class="box-team-side">
            <div class="box-ceopardy-colorless box-score">
              <p>${{ team.score }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
