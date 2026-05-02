<script setup>
import { computed, ref } from "vue";
import { api } from "@/api";
import { useGameStore } from "@/stores/game";

const game = useGameStore();
const customText = ref("");

const isOpen = computed(() => game.ui_state["container-footer"] === "slide-up");
const currentMessage = computed(() => game.ui_state.message);

async function toggle() {
  const next = isOpen.value ? "" : "slide-up";
  game.ui_state["container-footer"] = next;
  await api.setSliderState("container-footer", next);
}

async function toggleMessage(idx) {
  const mid = `message${idx + 1}`;
  if (mid === currentMessage.value) {
    await api.hideMessage();
    return;
  }
  const msg = game.messages[idx];
  // The "Custom" entry has an empty body and reads from the edit box.
  const text = msg.text || customText.value || "";
  await api.showMessage(mid, text);
}

async function hideAll() {
  await api.hideMessage();
}

const customEditing = ref(false);
function toggleCustom() {
  customEditing.value = !customEditing.value;
}
</script>

<template>
  <div
    class="container-footer container-slider flex-border-footer container-light"
    :class="game.ui_state['container-footer']"
  >
    <div class="container-arrow container-dark" @click="toggle">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 100 50"
        preserveAspectRatio="none"
      >
        <polygon points="0,50 50,0 100,50 50,25 0,50" />
      </svg>
    </div>

    <div style="display: flex; width: 100%">
      <div class="container-footer-control container-padding">
        <div class="form-row form-color">
          <p class="form-header">Messages</p>
          <div
            class="form-icon form-click"
            title="Hide any message"
            @click="hideAll"
          >
            <i class="fa-regular fa-eye-slash fa-lg" />
          </div>
        </div>

        <div
          v-for="(m, idx) in game.messages"
          :key="idx"
          class="message-parent"
        >
          <div class="form-row form-color team-info">
            <div class="form-text">{{ m.title }}</div>
            <div class="form-expand" />
            <div
              v-if="m.title === 'Custom'"
              class="form-icon form-click"
              @click="toggleCustom"
            >
              <i class="fa-solid fa-pen-to-square fa-lg" />
            </div>
            <div
              class="form-icon form-click"
              :title="
                currentMessage === `message${idx + 1}`
                  ? 'Hide message'
                  : 'Show message'
              "
              @click="toggleMessage(idx)"
            >
              <i
                :class="
                  currentMessage === `message${idx + 1}`
                    ? 'fa-regular fa-eye-slash'
                    : 'fa-regular fa-eye'
                "
                class="fa-lg"
              />
            </div>
          </div>
        </div>

        <div class="form-expand">
          <div
            v-if="customEditing"
            class="form-color form-edit"
            contenteditable="true"
            @input="customText = $event.target.innerText"
          >
            <span>{{ customText }}</span>
          </div>
        </div>
      </div>

      <div class="container-separator-v container-dark" />

      <div class="container-footer-control">
        <!--
          Monitor the crowd view so the host can see exactly what players see.
          Using an iframe is intentional: the crowd screen stays a fully
          standalone route.
        -->
        <iframe class="iframe-viewer" src="/" />
      </div>
    </div>
  </div>
</template>
