<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
// Crowd-facing UI. Listens to the store for state changes pushed from the
// server and renders the big Jeopardy board. The viewer is silent — all
// sounds (buzzers, daily-double, etc.) play on the host machine only.
import ViewerBoard from "@/components/ViewerBoard.vue";
import QuestionOverlay from "@/components/QuestionOverlay.vue";
import BigOverlay from "@/components/BigOverlay.vue";
</script>

<template>
  <div>
    <ViewerBoard />
    <QuestionOverlay />
    <BigOverlay />
  </div>
</template>
