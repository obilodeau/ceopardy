<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup>
import { reactive, watch } from "vue";
import { api } from "@/api";
import { useGameStore } from "@/stores/game";

const game = useGameStore();

const names = reactive({});
const errors = reactive({});

// Keep local form names in sync with the store. The store is the source of
// truth; the form just edits a copy until the host clicks Save.
watch(
  () => game.teams,
  (teams) => {
    for (const t of teams) names[t.tid] = t.name;
  },
  { immediate: true, deep: true },
);

const isOpen = () => game.ui_state["container-header"] === "slide-down";

async function toggle() {
  const next = isOpen() ? "" : "slide-down";
  game.ui_state["container-header"] = next;
  await api.setSliderState("container-header", next);
}

async function save() {
  for (const k of Object.keys(errors)) delete errors[k];
  try {
    await api.updateTeams(names);
    // Close drawer only on success.
    if (isOpen()) toggle();
  } catch (e) {
    errors.form = e.message;
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
