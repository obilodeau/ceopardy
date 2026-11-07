// SPDX-License-Identifier: GPL-3.0-or-later
import { ref } from "vue";

import { useGameStore } from "@/stores/game";

// The single audio layer for the whole app. Both the host and the viewer go
// through it; who actually makes noise is decided by isAudioSink() below, so
// no caller has to know about online mode.
//
// The sound registry (name -> URL) is served by the back-end in
// /api/v1/state, from SOUND_FILES in ceopardy/utils.py. Adding a sound is a
// back-end-only change.

// A one-sample silent WAV. Used to satisfy the autoplay policy without
// depending on a real sound file, most of which are gitignored.
const SILENCE =
  "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";

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

// Remote soundboard sounds, oldest first. Kept apart from thinkingAudio so
// Stop all can never cut the waiting music.
const MAX_SOUNDBOARD = 8;
const soundboardAudio: HTMLAudioElement[] = [];
let soundboardVolume = 0.85;

function dropSoundboard(audio: HTMLAudioElement): void {
  const i = soundboardAudio.indexOf(audio);
  if (i !== -1) soundboardAudio.splice(i, 1);
}

function makeAudio(url: string): HTMLAudioElement {
  const audio = new Audio(url);
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
  const game = useGameStore();

  /** URL for a sound, or "" when the back-end does not know that name. */
  function urlFor(name: string): string {
    return game.sounds[name] ?? "";
  }

  function play(name: string): void {
    if (!isAudioSink()) return;
    const url = urlFor(name);
    if (!url) return;
    try {
      makeAudio(url)
        .play()
        .catch(() => {});
    } catch {
      /* ignore */
    }
  }

  function startThinking(): void {
    if (!isAudioSink()) return;
    if (thinkingAudio && !thinkingAudio.paused) return;
    const url = urlFor("thinking");
    if (!url) return;
    try {
      thinkingAudio = makeAudio(url);
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

  function playSoundboard(url: string, percent: number): void {
    // Unlike the game's cues, nothing can replay a soundboard press, so wait
    // for the enable-sound click rather than gamble on autoplay.
    if (!isAudioSink() || !audioUnlocked.value) return;
    while (soundboardAudio.length >= MAX_SOUNDBOARD) {
      const oldest = soundboardAudio.shift();
      oldest?.pause();
    }
    try {
      soundboardVolume = percent / 100;
      const audio = makeAudio(url);
      audio.volume = soundboardVolume;
      soundboardAudio.push(audio);
      audio.addEventListener("ended", () => dropSoundboard(audio));
      audio.addEventListener("error", () => dropSoundboard(audio));
      audio.play().catch(() => dropSoundboard(audio));
    } catch {
      /* ignore */
    }
  }

  function stopSoundboard(): void {
    for (const audio of soundboardAudio.splice(0)) audio.pause();
  }

  function setSoundboardVolume(percent: number): void {
    soundboardVolume = percent / 100;
    for (const audio of soundboardAudio) audio.volume = soundboardVolume;
  }

  /**
   * Handle a one-shot `sound` broadcast from the server.
   *
   * The waiting music is not handled here: it is stateful, so it is driven
   * by watching the store's isThinking instead, which also covers clients
   * that join or reload in the middle of a break.
   */
  function handle(name: string, action: string): void {
    if (name === "thinking") return;
    if (action === "play") play(name);
  }

  /**
   * Satisfy the autoplay policy from inside a click handler by playing a
   * muted clip. Afterwards the tab is allowed to play audio on its own.
   */
  function unlock(): void {
    try {
      const audio = makeAudio(SILENCE);
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
    playSoundboard,
    stopSoundboard,
    setSoundboardVolume,
    handle,
    unlock,
    isAudioSink,
  };
}
