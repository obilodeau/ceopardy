// SPDX-License-Identifier: GPL-3.0-or-later
import { ref } from "vue";

import { useGameStore } from "@/stores/game";

// The single audio layer for the whole app. Both the host and the viewer go
// through it; who actually makes noise is decided by isAudioSink() below, so
// no caller has to know about online mode.
//
// Keep the names in sync with SOUND_NAMES in ceopardy/utils.py.
export type SoundName =
  | "buzzer1"
  | "buzzer2"
  | "buzzer3"
  | "timeout"
  | "reveal"
  | "thinking"
  | "dailydouble";

const soundUrls: Record<SoundName, string> = {
  buzzer1: "/static/sounds/buzzer1.wav",
  buzzer2: "/static/sounds/buzzer2.wav",
  buzzer3: "/static/sounds/buzzer3.wav",
  timeout: "/static/sounds/timeout.mp3",
  reveal: "/static/sounds/reveal.mp3",
  thinking: "/static/sounds/thinking-music.wav",
  dailydouble: "/static/sounds/daily-double.mp3",
};

export function isSoundName(name: string): name is SoundName {
  return name in soundUrls;
}

const UNLOCK_KEY = "ceopardy-audio-unlocked";

function readUnlocked(): boolean {
  try {
    return sessionStorage.getItem(UNLOCK_KEY) === "1";
  } catch {
    return false;
  }
}

// Browsers refuse to play audio until the tab has seen a user gesture. The
// host has always clicked something before the first sound, but a viewer on
// a shared screen may not have, so the viewer asks for one click up front.
export const audioUnlocked = ref(readUnlocked());

// Long-lived handle for the only sound with duration.
let thinkingAudio: HTMLAudioElement | null = null;

function makeAudio(name: SoundName): HTMLAudioElement {
  const audio = new Audio(soundUrls[name]);
  // Most sound files are gitignored (licensing), so a fresh clone 404s on
  // them. Never let that surface as an unhandled rejection.
  audio.addEventListener("error", () => {});
  return audio;
}

/**
 * True when THIS window is the one that should make noise.
 *
 * The host page embeds a live viewer in an iframe (HostFooterDrawer), which
 * would otherwise play everything a second time — and would make the host
 * loud in online mode, which is precisely what we are trying to avoid.
 */
export function isAudioSink(): boolean {
  if (typeof window !== "undefined" && window.self !== window.top) return false;
  const game = useGameStore();
  return game.onlineMode ? !game.isHost : game.isHost;
}

export function useSound() {
  function play(name: SoundName): void {
    if (!isAudioSink()) return;
    try {
      makeAudio(name)
        .play()
        .catch(() => {});
    } catch {
      /* ignore */
    }
  }

  function startThinking(): void {
    if (!isAudioSink()) return;
    if (thinkingAudio && !thinkingAudio.paused) return;
    try {
      thinkingAudio = makeAudio("thinking");
      // Waiting music has to keep going for the whole break.
      thinkingAudio.loop = true;
      thinkingAudio.play().catch(() => {});
    } catch {
      /* ignore */
    }
  }

  function stopThinking(): void {
    if (!thinkingAudio) return;
    thinkingAudio.pause();
    thinkingAudio.currentTime = 0;
    thinkingAudio = null;
  }

  /**
   * Handle a one-shot `sound` broadcast from the server.
   *
   * The waiting music is not handled here: it is stateful, so it is driven
   * by watching the store's isThinking instead, which also covers clients
   * that join or reload in the middle of a break.
   */
  function handle(name: string, action: string): void {
    if (!isSoundName(name) || name === "thinking") return;
    if (action === "play") play(name);
  }

  /**
   * Satisfy the autoplay policy from inside a click handler by playing a
   * muted clip. Afterwards the tab is allowed to play audio on its own.
   */
  function unlock(): void {
    try {
      const audio = makeAudio("buzzer1");
      audio.muted = true;
      audio
        .play()
        .then(() => {
          audio.pause();
          audio.currentTime = 0;
        })
        .catch(() => {});
    } catch {
      /* ignore */
    }
    audioUnlocked.value = true;
    try {
      sessionStorage.setItem(UNLOCK_KEY, "1");
    } catch {
      /* ignore */
    }
  }

  return {
    audioUnlocked,
    play,
    startThinking,
    stopThinking,
    handle,
    unlock,
    isAudioSink,
  };
}
