<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { api } from "@/api";
import { useGameStore } from "@/stores/game";
import type { BuzzerLinksResponse, Team } from "@/types";

const game = useGameStore();

const names = reactive<Record<string, string>>({});
const errors = reactive<Record<string, string>>({});

// Keep local form names in sync with the store. The store is the source of
// truth; the form just edits a copy until the host clicks Save.
watch(
  () => game.teams,
  (teams) => {
    for (const t of teams) names[t.tid] = t.name;
  },
  { immediate: true, deep: true },
);

const isOpen = (): boolean =>
  game.ui_state["container-header"] === "slide-down";

async function toggle(): Promise<void> {
  const next = isOpen() ? "" : "slide-down";
  game.ui_state["container-header"] = next;
  await api.setSliderState("container-header", next);
}

// ---- Web buzzer links (online mode) ----
// Fetched on demand rather than kept in the store: links carry each team's
// secret, and nothing else in the UI needs them.
const buzzerLinks = ref<BuzzerLinksResponse | null>(null);
const copiedTid = ref("");

async function fetchLinks(): Promise<void> {
  try {
    buzzerLinks.value = await api.buzzerLinks();
    game.buzzerPresence = buzzerLinks.value.presence;
  } catch (e) {
    errors.form = e instanceof Error ? e.message : String(e);
  }
}

watch(
  () => [game.onlineMode, isOpen(), game.buzzerLinksVersion] as const,
  ([online, open]) => {
    if (online && open) fetchLinks();
  },
  { immediate: true },
);

async function copyLink(team: Team): Promise<void> {
  const url = buzzerLinks.value?.links[team.tid];
  if (!url) return;
  try {
    await navigator.clipboard.writeText(url);
  } catch {
    // No Clipboard API outside a secure context (the host UI opened over
    // plain HTTP on a LAN address): let the host copy it by hand.
    window.prompt(`Copy ${team.name}'s buzzer link:`, url);
    return;
  }
  copiedTid.value = team.tid;
  setTimeout(() => {
    if (copiedTid.value === team.tid) copiedTid.value = "";
  }, 1500);
}

async function rotateLink(team: Team): Promise<void> {
  const ok = window.confirm(
    `Give ${team.name} a new buzzer link? Their players are disconnected ` +
      "until you send them the new one.",
  );
  if (!ok) return;
  await api.rotateBuzzerLink(team.tid);
  await fetchLinks();
}

const presence = (tid: string): number => game.buzzerPresence[tid] ?? 0;

async function save(): Promise<void> {
  for (const k of Object.keys(errors)) delete errors[k];
  try {
    await api.updateTeams(names);
    // Close drawer only on success.
    if (isOpen()) toggle();
  } catch (e) {
    errors.form = e instanceof Error ? e.message : String(e);
  }
}
</script>

<template>
  <div
    class="container-header container-slider flex-border-header container-light"
    :class="game.ui_state['container-header']"
  >
    <div style="display: flex; width: 100%">
      <div class="container-header-control container-padding">
        <div class="form-row form-color">
          <p class="form-header">Teams</p>
        </div>
        <form @submit.prevent="save">
          <div
            v-for="team in game.teams"
            :key="team.tid"
            class="form-row form-color team-info"
          >
            <div class="form-text">{{ team.tid }}</div>
            <input
              v-model="names[team.tid]"
              class="form-expand form-cursive form-text form-color form-no-form team-name"
              autocomplete="off"
              placeholder="Enter the name of the team"
            />
            <template v-if="game.onlineMode">
              <!-- divs, like the Save icon: a button would submit the form -->
              <div
                class="form-icon form-click"
                :class="{ disabled: !buzzerLinks?.links[team.tid] }"
                :title="`Copy ${team.name}'s buzzer link, to send only to them`"
                @click="copyLink(team)"
              >
                <i
                  class="fa-2x fa-fw"
                  :class="
                    copiedTid === team.tid
                      ? 'fa-solid fa-check'
                      : 'fa-regular fa-copy'
                  "
                />
              </div>
              <div
                class="form-icon form-click"
                :title="`Give ${team.name} a new buzzer link`"
                @click="rotateLink(team)"
              >
                <i class="fa-solid fa-key fa-2x fa-fw" />
              </div>
              <div
                class="form-icon form-text buzzer-presence"
                :class="{ joined: presence(team.tid) > 0 }"
                :title="`${presence(team.tid)} player(s) connected`"
              >
                <i class="fa-solid fa-user" />&nbsp;{{ presence(team.tid) }}
              </div>
            </template>
          </div>
          <div
            v-if="game.onlineMode && buzzerLinks"
            class="form-row form-color buzzer-status"
          >
            <span v-if="buzzerLinks.tunnel !== 'none'">
              Buzzers: {{ buzzerLinks.public_url }}
            </span>
            <span v-else class="form-error">
              <i class="fa-solid fa-triangle-exclamation" /> Buzzer links only
              work on this machine. Set NGROK_AUTHTOKEN and restart to share
              them.
            </span>
          </div>
          <div v-if="errors.form" class="form-error">{{ errors.form }}</div>
          <div class="form-row form-color">
            <div class="form-expand" />
            <div
              class="form-icon form-click"
              title="Save team names"
              @click="save"
            >
              <i class="fa-solid fa-rotate fa-2x" />
            </div>
            <div class="form-expand" />
          </div>
          <input type="submit" style="display: none" />
        </form>
      </div>
    </div>

    <div class="container-arrow container-dark" @click="toggle">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 100 50"
        preserveAspectRatio="none"
      >
        <polygon points="0,0 50,50 100,0 50,25 0,0" />
      </svg>
    </div>
  </div>
</template>
