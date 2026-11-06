<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { io, type Socket } from "socket.io-client";

import { takeToken } from "@/links/token";

type Phase =
  | "connecting"
  | "reconnecting"
  | "invalid"
  | "full"
  | "revoked"
  | "ready";

interface Sound {
  id: string;
  label: string;
}

const TOKEN_KEY = "ceopardy-soundboard-token";
const SENT_MS = 700;

const MESSAGES: Record<Exclude<Phase, "ready">, string> = {
  connecting: "Connecting…",
  reconnecting: "Connection lost, reconnecting…",
  invalid: "This link isn't valid. Ask the host for the soundboard link.",
  full: "Too many soundboards are open on this link.",
  revoked: "This link is no longer valid. Ask the host for a new one.",
};

const phase = ref<Phase>("connecting");
const sounds = ref<Sound[]>([]);
const sent = reactive(new Set<string>());
const connected = computed(() => phase.value === "ready");
const message = computed(() => {
  if (phase.value !== "ready") return MESSAGES[phase.value];
  if (sounds.value.length === 0) {
    return "No sounds. Ask the host to put audio files in the soundboard folder, then refresh.";
  }
  return "Sounds play on the stream. Expect the stream's usual lag.";
});

let socket: Socket | null = null;
const sentTimers = new Map<string, ReturnType<typeof setTimeout>>();

function flash(key: string): void {
  sent.add(key);
  const previous = sentTimers.get(key);
  if (previous) clearTimeout(previous);
  sentTimers.set(
    key,
    setTimeout(() => {
      sent.delete(key);
      sentTimers.delete(key);
    }, SENT_MS),
  );
}

function play(sound: Sound): void {
  if (!connected.value) return;
  socket?.emit("play", { id: sound.id });
  flash(sound.id);
}

function stopAll(): void {
  if (!connected.value) return;
  socket?.emit("stop", {});
  flash("stop");
}

function refresh(): void {
  if (!connected.value) return;
  socket?.emit("refresh", {});
}

function connect(token: string): void {
  const s = io("/soundboard", {
    path: "/guest-io",
    auth: { token },
    transports: ["websocket", "polling"],
  });
  socket = s;

  s.on("connect", () => {
    phase.value = "ready";
  });
  s.on("connect_error", (err: Error) => {
    if (err.message === "invalid link" || err.message === "full") {
      phase.value = err.message === "invalid link" ? "invalid" : "full";
      s.disconnect();
    } else {
      phase.value = "reconnecting";
    }
  });
  s.on("disconnect", () => {
    if (phase.value !== "revoked") phase.value = "reconnecting";
  });
  s.on("sounds", (data: { sounds: Sound[] }) => {
    sounds.value = data.sounds;
  });
  s.on("revoked", () => {
    phase.value = "revoked";
    sounds.value = [];
  });
}

onMounted(() => {
  const token = takeToken(TOKEN_KEY);
  if (!token) {
    phase.value = "invalid";
    return;
  }
  connect(token);
});

onBeforeUnmount(() => {
  socket?.disconnect();
  sentTimers.forEach((timer) => clearTimeout(timer));
});
</script>

<template>
  <main class="soundboard" :class="`phase-${phase}`">
    <h1 class="title">Soundboard</h1>
    <p class="status" role="status" aria-live="polite">{{ message }}</p>
    <div class="sounds">
      <button
        v-for="sound in sounds"
        :key="sound.id"
        type="button"
        class="sound"
        :class="{ sent: sent.has(sound.id) }"
        :disabled="!connected"
        @click="play(sound)"
      >
        <span class="label">{{ sound.label }}</span>
        <span class="feedback" aria-hidden="true">{{
          sent.has(sound.id) ? "sent" : ""
        }}</span>
      </button>
    </div>
    <div class="controls">
      <button
        type="button"
        class="stop"
        :class="{ sent: sent.has('stop') }"
        :disabled="!connected"
        @click="stopAll"
      >
        {{ sent.has("stop") ? "Stop sent" : "Stop all" }}
      </button>
      <button
        type="button"
        class="refresh"
        :disabled="!connected"
        @click="refresh"
      >
        Refresh
      </button>
    </div>
  </main>
</template>

<style>
html,
body,
#app {
  min-height: 100%;
  margin: 0;
}
body {
  background: #391f0c;
  font-family:
    -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
}
</style>

<style scoped>
.soundboard {
  --gold: #d9a24f;
  --blue: #0001a1;
  --idle: #4a4a5a;
  --go: #1fa64a;
  --stop: #d32f2f;
  box-sizing: border-box;
  min-height: 100vh;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: #ffffff;
  user-select: none;
  -webkit-user-select: none;
}

.title {
  margin: 0;
  color: var(--gold);
  text-shadow: 2px 2px 0 #000000;
  font-size: clamp(24px, 6vw, 40px);
  text-align: center;
}

.status {
  margin: 0;
  min-height: 1.4em;
  text-align: center;
  font-size: clamp(16px, 4vw, 20px);
}

.sounds {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

button {
  font: inherit;
  font-weight: bold;
  color: #ffffff;
  border: 4px solid #000000;
  border-radius: 12px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    background-color 80ms,
    transform 80ms;
}
button:focus-visible {
  outline: 4px solid var(--gold);
  outline-offset: 2px;
}
button:active:not(:disabled) {
  transform: scale(0.96);
}
button:disabled {
  opacity: 0.35;
  cursor: default;
}

.sound {
  min-height: 88px;
  padding: 8px;
  background: var(--blue);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.sound .label {
  overflow-wrap: anywhere;
  font-size: 18px;
}
.sound .feedback {
  min-height: 1.2em;
  font-size: 13px;
  font-weight: normal;
  color: var(--gold);
}
.sound.sent {
  background: var(--go);
}

.controls {
  display: flex;
  gap: 12px;
}
.stop {
  flex: 1;
  min-height: 64px;
  background: var(--stop);
  font-size: 20px;
}
.stop.sent {
  background: #8e1f1f;
}
.refresh {
  min-height: 64px;
  padding: 0 20px;
  background: var(--idle);
}
</style>
