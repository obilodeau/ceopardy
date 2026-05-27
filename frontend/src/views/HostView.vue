<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api";
import { useGameStore } from "@/stores/game";

import HostBoard from "@/components/HostBoard.vue";
import HostControls from "@/components/HostControls.vue";
import HostHeaderDrawer from "@/components/HostHeaderDrawer.vue";
import HostFooterDrawer from "@/components/HostFooterDrawer.vue";
import TeamScoringPanel from "@/components/TeamScoringPanel.vue";

type AnswerMap = Record<string, number>;
type SoundName =
  | "buzzer1"
  | "buzzer2"
  | "buzzer3"
  | "timeout"
  | "reveal"
  | "thinking"
  | "dailydouble";

const router = useRouter();
const game = useGameStore();

// Local form state for the per-team answer sliders.
const answers = ref<AnswerMap>({});

function resetAnswers(): void {
  const next: AnswerMap = {};
  for (const t of game.teams) next[t.tid] = 0;
  answers.value = next;
}

onMounted(async () => {
  game.isHost = true;
  if (!game.initialized) await game.refresh();
  if (!game.isInProgress) {
    router.push({ name: "start" });
    return;
  }
  resetAnswers();
});

// Whenever a new question gets selected, reset the slider values so we don't
// carry state from a previous question.
watch(
  () => game.activeQuestionId,
  (qid, oldQid) => {
    if (qid !== oldQid) resetAnswers();
  },
);

// ---- Buzzer handling ----
const buzzersLocked = ref(true);
function toggleBuzzers(): void {
  buzzersLocked.value = !buzzersLocked.value;
}
function lockBuzzers(): void {
  buzzersLocked.value = true;
}
function unlockBuzzers(): void {
  buzzersLocked.value = false;
}

// Keyboard events from the emulated-keyboard buzzers.
function onKeyPress(e: KeyboardEvent): void {
  if (buzzersLocked.value) return;
  // Only numeric keys 1..N.
  const num = parseInt(e.key, 10);
  if (!Number.isInteger(num)) return;
  if (num < 1 || num > game.teams.length) return;
  const tid = `team${num}`;
  api.selectTeam(tid);
  playSound(`buzzer${num}` as SoundName);
  lockBuzzers();
}

onMounted(() => {
  window.addEventListener("keypress", onKeyPress);
});

// ---- Question selection ----
async function onSelectQuestion(qid: string): Promise<void> {
  if (game.activeQuestionId === qid) {
    await api.deselectQuestion();
    lockBuzzers();
    return;
  }
  const data = await api.selectQuestion(qid);
  if (data?.dailydouble) {
    if (data.dailydouble_range) game.dailydouble_range = data.dailydouble_range;
    if (data.team) game.ui_state.team = data.team;
    // No buzzer race in a Daily Double — only the controlling team plays.
    lockBuzzers();
    playSound("dailydouble");
  } else {
    unlockBuzzers();
  }
}

// ---- Submitting answers ----
async function submitAnswers(): Promise<void> {
  if (!game.activeQuestionId) return;
  const payload = { id: game.activeQuestionId, answers: answers.value };
  const res = await api.submitAnswer(payload);
  if (res?.result === "success") {
    await api.deselectQuestion();
    lockBuzzers();
  }
}

// ---- Roulette / finish / sounds ----
function onRoulette(): void {
  api.roulette();
}
async function onFinish(): Promise<void> {
  if (
    window.confirm("Bring the game to the final round (if any). Are you sure?")
  ) {
    await api.finish();
    router.push({ name: "start" });
  }
}
function playTimeout(): void {
  playSound("timeout");
}

const soundUrls: Record<SoundName, string> = {
  buzzer1: "/static/sounds/buzzer1.wav",
  buzzer2: "/static/sounds/buzzer2.wav",
  buzzer3: "/static/sounds/buzzer3.wav",
  timeout: "/static/sounds/timeout.mp3",
  reveal: "/static/sounds/reveal.mp3",
  thinking: "/static/sounds/thinking-music.wav",
  dailydouble: "/static/sounds/daily-double.mp3",
};
const preloaded: Partial<Record<SoundName, HTMLAudioElement>> = {};
for (const [name, url] of Object.entries(soundUrls) as [SoundName, string][]) {
  const a = new Audio(url);
  a.preload = "auto";
  preloaded[name] = a;
}

let thinkingAudio: HTMLAudioElement | null = null;
function playSound(name: SoundName): void {
  try {
    const audio = new Audio(soundUrls[name]);
    audio.play().catch(() => {});
  } catch {
    /* ignore */
  }
}
function toggleThinking(): void {
  if (thinkingAudio && !thinkingAudio.paused) {
    thinkingAudio.pause();
    thinkingAudio.currentTime = 0;
    thinkingAudio = null;
  } else {
    thinkingAudio = new Audio(soundUrls.thinking);
    thinkingAudio.play().catch(() => {});
  }
}

// Automatically unlock buzzers if any team is marked "Bad" so it can buzz in
// again.
watch(
  answers,
  (val) => {
    for (const t of game.teams) {
      if (val[t.tid] === -1) {
        unlockBuzzers();
        break;
      }
    }
  },
  { deep: true },
);

const activeHtml = computed(() => {
  if (game.isDailyDouble && !game.isDailyDoubleRevealed) {
    return "<p>Daily Double!<br/>Please input user bet.</p>";
  }
  return game.active_question?.text ?? "";
});

const canRevealDailyDouble = computed(
  () =>
    game.isDailyDouble &&
    !game.isDailyDoubleRevealed &&
    game.dailydouble_wager != null,
);

async function onRevealDailyDouble(): Promise<void> {
  await api.revealDailyDouble();
}
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
        @thinking="toggleThinking"
        @toggle-buzzers="toggleBuzzers"
        @submit="submitAnswers"
        @finish="onFinish"
      />

      <form class="container-bottom-middle" @submit.prevent="submitAnswers">
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
            <div class="box-ceopardy box-question-host" v-html="activeHtml" />
            <button
              v-if="canRevealDailyDouble"
              type="button"
              class="dd-reveal-btn"
              @click="onRevealDailyDouble"
            >
              <i class="fa-solid fa-eye" /> Reveal clue
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="container-all container-light" style="height: 35px" />

    <HostFooterDrawer />
  </div>
</template>
