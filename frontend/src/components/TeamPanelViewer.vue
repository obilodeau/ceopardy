<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { computed } from "vue";
import { useGameStore } from "@/stores/game";
import type { Team } from "@/types";

const props = withDefaults(
  defineProps<{
    team: Team;
    idx: number;
    selected?: boolean;
  }>(),
  { selected: false },
);

const game = useGameStore();
const margin = computed(() => game.closeMarginOf(props.team.tid));
</script>

<template>
  <div
    :id="team.tid"
    class="black-box flex-pad"
    :class="{ 'team-selected': selected }"
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
          <Transition name="close-margin">
            <p v-if="margin !== undefined && !selected" class="close-margin">
              +{{ margin }} ms
            </p>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>
