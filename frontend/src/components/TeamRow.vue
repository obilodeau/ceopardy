<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { useGameStore } from "@/stores/game";
import TeamPanelViewer from "@/components/TeamPanelViewer.vue";

const game = useGameStore();
</script>

<template>
  <div class="container-results">
    <div
      v-for="(team, idx) in game.teams"
      :key="team.tid"
      class="container-team"
    >
      <TeamPanelViewer
        :team="team"
        :idx="idx"
        :selected="game.selectedTeam === team.tid"
      />
    </div>
  </div>
</template>
