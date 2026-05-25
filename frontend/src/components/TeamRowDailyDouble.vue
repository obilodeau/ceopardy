<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup>
import { computed } from "vue";
import { useGameStore } from "@/stores/game";
import TeamPanelViewer from "@/components/TeamPanelViewer.vue";

const game = useGameStore();

// Resolve the team currently in control (the one playing the DD). Falls back
// to null while the operator hasn't picked one yet — the layout still renders
// so the row doesn't pop in/out, but we leave the panel slot empty.
const playingIdx = computed(() =>
  game.teams.findIndex((t) => t.tid === game.selectedTeam),
);
const playingTeam = computed(() =>
  playingIdx.value >= 0 ? game.teams[playingIdx.value] : null,
);

// Live wager from the host's slider. May be null until the operator nudges it.
const wagerAmount = computed(() => game.dailydouble_wager?.amount ?? null);
</script>

<template>
  <div class="container-results">
    <!-- Slot 1: the playing team's panel -->
    <div class="container-team">
      <TeamPanelViewer
        v-if="playingTeam"
        :team="playingTeam"
        :idx="playingIdx"
        :selected="true"
      />
    </div>

    <!-- Slots 2..N: a single mask box covering the rest with wager + score -->
    <div
      class="container-team dd-info-box-wrap"
      :style="{ flexGrow: Math.max(1, game.teams.length - 1) }"
    >
      <div
        class="black-box flex-pad"
        style="width: 100%; max-width: 600px; margin: auto"
      >
        <div class="box-ceopardy dd-info-box-inner">
          <span class="dd-info-label">Wager:</span>
          <span class="dd-info-amount">
            {{ wagerAmount == null ? "all in?" : `$${wagerAmount}` }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
