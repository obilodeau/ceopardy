<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useGameStore } from '@/stores/game'

import HostBoard from '@/components/HostBoard.vue'
import HostControls from '@/components/HostControls.vue'
import HostHeaderDrawer from '@/components/HostHeaderDrawer.vue'
import HostFooterDrawer from '@/components/HostFooterDrawer.vue'
import TeamScoringPanel from '@/components/TeamScoringPanel.vue'

const router = useRouter()
const game = useGameStore()

// Local form state for the per-team answer sliders.
const answers = ref({})

function resetAnswers() {
  const next = {}
  for (const t of game.teams) next[t.tid] = 0
  answers.value = next
}

onMounted(async () => {
  if (!game.initialized) await game.refresh()
  if (!game.isInProgress) {
    router.push({ name: 'start' })
    return
  }
  resetAnswers()
})

// Whenever a new question gets selected, reset the slider values so we don't
// carry state from a previous question.
watch(
  () => game.activeQuestionId,
  (qid, oldQid) => {
    if (qid !== oldQid) resetAnswers()
  },
)

// ---- Buzzer handling ----
const buzzersLocked = ref(true)
function toggleBuzzers() {
  buzzersLocked.value = !buzzersLocked.value
}
function lockBuzzers() {
  buzzersLocked.value = true
}
function unlockBuzzers() {
  buzzersLocked.value = false
}

// Keyboard events from the emulated-keyboard buzzers.
function onKeyPress(e) {
  if (buzzersLocked.value) return
  // Only numeric keys 1..N.
  const num = parseInt(e.key, 10)
  if (!Number.isInteger(num)) return
  if (num < 1 || num > game.teams.length) return
  const tid = `team${num}`
  api.selectTeam(tid)
  playSound(`buzzer${num}`)
  lockBuzzers()
}

onMounted(() => {
  window.addEventListener('keypress', onKeyPress)
})

// ---- Question selection ----
async function onSelectQuestion(qid) {
  if (game.activeQuestionId === qid) {
    await api.deselectQuestion()
    lockBuzzers()
    return
  }
  const data = await api.selectQuestion(qid)
  if (data?.dailydouble) {
    playSound('dailydouble')
  } else {
    unlockBuzzers()
  }
}

// ---- Submitting answers ----
async function submitAnswers() {
  if (!game.activeQuestionId) return
  const payload = { id: game.activeQuestionId, answers: answers.value }
  const res = await api.submitAnswer(payload)
  if (res?.result === 'success') {
    await api.deselectQuestion()
    lockBuzzers()
  }
}

// ---- Roulette / finish / sounds ----
function onRoulette() {
  api.roulette()
}
async function onFinish() {
  if (
    window.confirm('Bring the game to the final round (if any). Are you sure?')
  ) {
    await api.finish()
  }
}
function playTimeout() {
  playSound('timeout')
}

const soundUrls = {
  buzzer1: '/static/sounds/buzzer1.wav',
  buzzer2: '/static/sounds/buzzer2.wav',
  buzzer3: '/static/sounds/buzzer3.wav',
  timeout: '/static/sounds/timeout.mp3',
  reveal: '/static/sounds/reveal.mp3',
  thinking: '/static/sounds/thinking-music.wav',
  dailydouble: '/static/sounds/daily-double.mp3',
}
function playSound(name) {
  try {
    const audio = new Audio(soundUrls[name])
    audio.play().catch(() => {})
  } catch {
    /* ignore */
  }
}

// Automatically unlock buzzers if any team is marked "Bad" so it can buzz in
// again.
watch(
  answers,
  (val) => {
    for (const t of game.teams) {
      if (val[t.tid] === -1) {
        unlockBuzzers()
        break
      }
    }
  },
  { deep: true },
)

// ---- Active question HTML (for the preview panel) ----
const activeHtml = computed(() => {
  if (game.isDailyDouble) {
    return '<p>Daily Double!<br/>Please input user bet.</p>'
  }
  return game.active_question?.text ?? ''
})
</script>

<template>
  <div class="container-host">
    <HostHeaderDrawer />

    <!-- Spacer for the top arrow -->
    <div class="container-all container-light" style="height: 35px" />

    <HostBoard @select="onSelectQuestion" />

    <div class="container-bottom container-all container-light">
      <HostControls
        :buzzers-locked="buzzersLocked"
        @roulette="onRoulette"
        @timeout="playTimeout"
        @toggle-buzzers="toggleBuzzers"
        @submit="submitAnswers"
        @finish="onFinish"
      />

      <form
        class="container-bottom-middle"
        @submit.prevent="submitAnswers"
      >
        <TeamScoringPanel
          v-for="(team, idx) in game.teams"
          :key="team.tid"
          :team="team"
          :idx="idx"
          :answers="answers"
          @update:answers="answers = $event"
        />
      </form>

      <div class="container-bottom-right">
        <div class="black-box flex-small-pad">
          <div class="box-fake-overlay">
            <div
              class="box-ceopardy box-question-host"
              v-html="activeHtml"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="container-all container-light" style="height: 35px" />

    <HostFooterDrawer />
  </div>
</template>
