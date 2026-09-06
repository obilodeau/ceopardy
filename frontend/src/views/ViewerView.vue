<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
// Crowd-facing UI. Listens to the store for state changes pushed from the
// server and renders the big Jeopardy board. Normally silent: sounds play on
// the host machine. Under `ceopardy serve --online` that flips and this view
// becomes the one making noise, since it is the tab being screen-shared.
import ViewerBoard from "@/components/ViewerBoard.vue";
import QuestionOverlay from "@/components/QuestionOverlay.vue";
import BigOverlay from "@/components/BigOverlay.vue";
import EnableSoundOverlay from "@/components/EnableSoundOverlay.vue";
</script>

<template>
  <div>
    <ViewerBoard />
    <QuestionOverlay />
    <BigOverlay />
    <EnableSoundOverlay />
  </div>
</template>
