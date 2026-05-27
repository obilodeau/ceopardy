<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
// Visibility is controlled by the parent: it mounts this component when DD
// becomes active and unmounts it when DD ends. The CSS animation runs once
// (`forwards`) so the card stays put after the flip.
</script>

<template>
  <div class="dailydouble-overlay">
    <div class="dailydouble-inner">
      <span>DAILY</span>
      <span>DOUBLE</span>
    </div>
  </div>
</template>
