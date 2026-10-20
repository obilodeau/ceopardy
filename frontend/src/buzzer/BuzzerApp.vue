<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { io, type Socket } from "socket.io-client";

type Phase =
  | "connecting"
  | "reconnecting"
  | "invalid"
  | "full"
  | "revoked"
  | "locked"
  | "open"
  | "early"
  | "buzzed"
  | "won"
  | "lost"
  | "excluded";

type Ack = () => void;

const TOKEN_KEY = "ceopardy-buzzer-token";
// Mirrors BUZZER_EARLY_LOCKOUT_MS; the server enforces it, this only shows it.
const EARLY_LOCKOUT_MS = 250;

const MESSAGES: Record<Phase, string> = {
  connecting: "Connecting…",
  reconnecting: "Connection lost, reconnecting…",
  invalid: "This link isn't valid. Ask the host for your team's link.",
  full: "Too many players on this team's link.",
  revoked: "This link is no longer valid. Ask the host for a new one.",
  locked: "Wait for the next question.",
  open: "Buzz!",
  early: "Too early!",
  buzzed: "Buzzed! Waiting for the other teams…",
  won: "You're in! Answer now.",
  lost: "Another team was faster.",
  excluded: "Your team already answered this one.",
};

const phase = ref<Phase>("connecting");
const teamName = ref("");
const message = computed(() => MESSAGES[phase.value]);
const live = computed(() => phase.value === "open");

let socket: Socket | null = null;
let epoch = 0;
let openedAt = 0;
let earlyTimer: ReturnType<typeof setTimeout> | null = null;
let phaseBeforeEarly: Phase = "locked";

// The token rides in the URL fragment, which browsers never send to a
// server. Move it to sessionStorage and out of the address bar, so it
// doesn't show on a player's own screen share; a reload still finds it.
function takeToken(): string {
  const fromHash = window.location.hash.slice(1);
  try {
    if (fromHash) {
      sessionStorage.setItem(TOKEN_KEY, fromHash);
    } else {
      return sessionStorage.getItem(TOKEN_KEY) ?? "";
    }
  } catch {
    // Storage blocked: keep the token in the URL so a reload still works.
    return fromHash;
  }
  history.replaceState(null, "", window.location.pathname);
  return fromHash;
}

function press(): void {
  if (phase.value === "open") {
    const reaction = performance.now() - openedAt;
    socket?.emit("buzz", {
      epoch,
      reaction_ms: Math.round(reaction * 10) / 10,
    });
    phase.value = "buzzed";
    navigator.vibrate?.(40);
  } else if (["locked", "won", "lost", "early"].includes(phase.value)) {
    // Tell the server too: an early press costs the next race a lockout.
    socket?.emit("buzz", { epoch, reaction_ms: 0 });
    if (phase.value !== "early") phaseBeforeEarly = phase.value;
    phase.value = "early";
    if (earlyTimer) clearTimeout(earlyTimer);
    earlyTimer = setTimeout(() => {
      earlyTimer = null;
      if (phase.value === "early") phase.value = phaseBeforeEarly;
    }, EARLY_LOCKOUT_MS);
  }
}

function onKey(e: KeyboardEvent): void {
  if (e.repeat || (e.key !== " " && e.key !== "Enter")) return;
  e.preventDefault();
  press();
}

let wakeLock: WakeLockSentinel | null = null;
async function keepAwake(): Promise<void> {
  if (document.visibilityState !== "visible" || wakeLock) return;
  try {
    wakeLock = (await navigator.wakeLock?.request("screen")) ?? null;
    wakeLock?.addEventListener("release", () => (wakeLock = null));
  } catch {
    // Not supported or refused: the page still works, the phone may sleep.
  }
}

function connect(token: string): void {
  const s = io("/buzz", {
    path: "/buzz-io",
    auth: { token },
    transports: ["websocket", "polling"],
  });
  socket = s;

  s.on("connect", () => {
    // "open" can arrive in the same tick, before this handler.
    if (phase.value === "connecting" || phase.value === "reconnecting") {
      phase.value = "locked";
    }
  });
  s.on("connect_error", (err: Error) => {
    if (err.message === "invalid link" || err.message === "team full") {
      phase.value = err.message === "invalid link" ? "invalid" : "full";
      s.disconnect();
    } else {
      phase.value = "reconnecting";
    }
  });
  s.on("disconnect", () => {
    if (phase.value !== "revoked") phase.value = "reconnecting";
  });

  s.on("team", (data: { name: string }) => {
    teamName.value = data.name;
  });
  s.on("open", (data: { epoch: number }, ack?: Ack) => {
    ack?.();
    openedAt = performance.now();
    epoch = data.epoch;
    phase.value = "open";
  });
  s.on("closed", (data: { won: boolean | null }) => {
    if (data.won === true) phase.value = "won";
    else if (data.won === false && phase.value !== "excluded")
      phase.value = "lost";
    else phase.value = "locked";
  });
  s.on("excluded", () => {
    phase.value = "excluded";
  });
  s.on("ping", (_data: unknown, ack?: Ack) => ack?.());
  s.on("revoked", () => {
    phase.value = "revoked";
  });
}

onMounted(() => {
  window.addEventListener("keydown", onKey);
  document.addEventListener("visibilitychange", keepAwake);
  const token = takeToken();
  if (!token) {
    phase.value = "invalid";
    return;
  }
  connect(token);
  keepAwake();
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKey);
  document.removeEventListener("visibilitychange", keepAwake);
  socket?.disconnect();
});
</script>

<template>
  <main class="buzzer" :class="`phase-${phase}`">
    <h1 class="team">{{ teamName || "Ceopardy" }}</h1>
    <button
      type="button"
      class="button"
      :aria-disabled="!live"
      @pointerdown.prevent="press"
    >
      BUZZ
    </button>
    <p class="status" role="status" aria-live="assertive">{{ message }}</p>
  </main>
</template>

<style>
html,
body,
#app {
  height: 100%;
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
.buzzer {
  --gold: #d9a24f;
  --blue: #0001a1;
  --idle: #4a4a5a;
  --go: #1fa64a;
  --early: #d32f2f;
  box-sizing: border-box;
  height: 100%;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-evenly;
  color: #ffffff;
  text-align: center;
  user-select: none;
  -webkit-user-select: none;
}

.team {
  margin: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  color: var(--gold);
  text-shadow: 2px 2px 0 #000000;
  font-size: clamp(28px, 8vw, 56px);
}

.button {
  width: min(80vw, 60vh, 420px);
  aspect-ratio: 1;
  border-radius: 50%;
  border: 10px solid #000000;
  background: var(--idle);
  color: rgba(255, 255, 255, 0.6);
  font: inherit;
  font-weight: bold;
  font-size: clamp(36px, 12vw, 80px);
  letter-spacing: 0.05em;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    background-color 80ms,
    transform 80ms;
}
.button:focus-visible {
  outline: 4px solid var(--gold);
  outline-offset: 4px;
}

.phase-open .button {
  background: var(--go);
  color: #ffffff;
  box-shadow: 0 0 40px var(--go);
}
.phase-open .button:active {
  transform: scale(0.96);
}
.phase-early .button {
  background: var(--early);
}
.phase-buzzed .button {
  background: var(--blue);
  color: #ffffff;
}
.phase-won .button {
  background: var(--gold);
  color: #000000;
  box-shadow: 0 0 40px var(--gold);
}
.phase-invalid .button,
.phase-full .button,
.phase-revoked .button,
.phase-excluded .button {
  opacity: 0.35;
  cursor: default;
}

.status {
  margin: 0;
  min-height: 2.6em;
  font-size: clamp(18px, 5vw, 28px);
}
</style>
