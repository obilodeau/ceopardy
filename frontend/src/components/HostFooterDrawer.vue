<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { api } from "@/api";
import { useGameStore } from "@/stores/game";

const game = useGameStore();
const customText = ref("");

const isOpen = computed(() => game.ui_state["container-footer"] === "slide-up");
const currentMessage = computed(() => game.ui_state.message);

// The "Custom" entry has an empty body and reads from the edit box instead.
// An operator is free to drop it from their MESSAGES config, hence the -1.
const customIdx = computed(() =>
  game.messages.findIndex((m) => m.title === "Custom"),
);
const customMid = computed(() =>
  customIdx.value >= 0 ? messageId(customIdx.value) : "",
);
const canSubmit = computed(
  () => customIdx.value >= 0 && customText.value.trim().length > 0,
);

function messageId(idx: number): string {
  return `message${idx + 1}`;
}

async function toggle(): Promise<void> {
  const next = isOpen.value ? "" : "slide-up";
  game.ui_state["container-footer"] = next;
  await api.setSliderState("container-footer", next);
}

// Submit always shows, never hides: it is "put this on the screen", which is
// what makes editing a message that is already up a single click.
async function showCustom(): Promise<void> {
  if (!canSubmit.value) return;
  await api.showMessage(customMid.value, customText.value.trim());
}

async function toggleMessage(idx: number): Promise<void> {
  if (messageId(idx) === currentMessage.value) {
    await api.hideMessage();
    return;
  }
  if (idx === customIdx.value) {
    await showCustom();
    return;
  }
  await api.showMessage(messageId(idx), game.messages[idx]?.text ?? "");
}

async function hideAll(): Promise<void> {
  await api.hideMessage();
}

const customEditing = ref(false);
const customInput = ref<HTMLInputElement | null>(null);

// Put the host back where they were after a reload: if the custom message is
// the one on screen, open the box and seed it from the text the server kept.
// This only ever opens the box; closing it stays the pencil's job. The
// empty-draft guard means a second host window never loses an unsent draft.
watch(
  () => [currentMessage.value, game.ui_state["message-text"]] as const,
  ([mid, text]) => {
    if (!customMid.value || mid !== customMid.value) return;
    customEditing.value = true;
    if (!customText.value) customText.value = text ?? "";
  },
  { immediate: true },
);

async function toggleCustom(): Promise<void> {
  customEditing.value = !customEditing.value;
  if (!customEditing.value) return;
  await nextTick();
  customInput.value?.focus();
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
              v-if="idx === customIdx"
              class="form-icon form-click"
              :title="customEditing ? 'Close the edit box' : 'Edit the message'"
              @click="toggleCustom"
            >
              <i class="fa-solid fa-pen-to-square fa-lg" />
            </div>
            <div
              class="form-icon form-click"
              :title="
                currentMessage === messageId(idx)
                  ? 'Hide message'
                  : 'Show message'
              "
              @click="toggleMessage(idx)"
            >
              <i
                :class="
                  currentMessage === messageId(idx)
                    ? 'fa-regular fa-eye-slash'
                    : 'fa-regular fa-eye'
                "
                class="fa-lg"
              />
            </div>
          </div>
        </div>

        <div class="form-expand">
          <form v-if="customEditing" @submit.prevent="showCustom">
            <input
              ref="customInput"
              v-model="customText"
              class="form-color form-edit form-no-form form-text"
              autocomplete="off"
              placeholder="Type a message for the crowd screen"
            />
            <div class="form-row form-color">
              <div class="form-expand" />
              <div
                class="form-icon form-click"
                :class="{ disabled: !canSubmit }"
                :title="
                  currentMessage === customMid
                    ? 'Update the message on screen'
                    : 'Show this message'
                "
                @click="showCustom"
              >
                <i class="fa-solid fa-paper-plane fa-2x" />
              </div>
              <div class="form-expand" />
            </div>
            <input type="submit" style="display: none" />
          </form>
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
