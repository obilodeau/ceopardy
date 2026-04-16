<script setup>
import { onMounted, ref } from 'vue'

const emit = defineEmits(['done'])
const visible = ref(true)

onMounted(() => {
  // Match CSS animation duration (2s) plus a small tail.
  setTimeout(() => {
    visible.value = false
    emit('done')
  }, 2200)
})
</script>

<template>
  <Transition name="fade">
    <div v-if="visible" class="dailydouble-overlay">
      <div class="dailydouble-inner">
        <span>DAILY</span>
        <span>DOUBLE</span>
      </div>
    </div>
  </Transition>
</template>
