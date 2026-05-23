<script setup>
defineProps({
  team: { type: Object, required: true },
  idx: { type: Number, required: true },
  selected: { type: Boolean, default: false },
});
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
        </div>
      </div>
    </div>
  </div>
</template>
