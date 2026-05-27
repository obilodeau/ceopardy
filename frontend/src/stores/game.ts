// SPDX-License-Identifier: GPL-3.0-or-later
import { defineStore } from "pinia";
import type { Socket } from "socket.io-client";

import { api } from "@/api";
import { getSocket } from "@/socket";
import type {
  ActiveQuestion,
  AppConfig,
  BoardUpdateEvent,
  DailyDoubleEvent,
  DailyDoubleRangeEvent,
  DailyDoubleRevealEvent,
  DailyDoubleWager,
  DailyDoubleWagerEvent,
  GameState,
  OverlayBigEvent,
  QuestionShowEvent,
  QuestionsMap,
  Range,
  RedirectEvent,
  ServerMessage,
  ServerState,
  SliderEvent,
  Team,
  TeamNamesEvent,
  TeamRouletteEvent,
  TeamSelectEvent,
  UiState,
} from "@/types";

// Single source of truth for the game state that both the host and viewer
// views read from. Server broadcasts keep this in sync across windows.

interface GameStoreState {
  initialized: boolean;
  config: AppConfig;
  game_state: GameState;
  teams: Team[];
  categories: string[];
  questions: QuestionsMap;
  ui_state: UiState;
  active_question: ActiveQuestion;
  messages: ServerMessage[];
  dailydouble_range: Range;
  dailydouble_wager: DailyDoubleWager | null;
  // Incremented every time the server fires a new daily-double. Lets the
  // viewer trigger the flip animation without watching for state changes
  // that might bounce during reconnects.
  dailydoubleTrigger: number;
  socket: Socket | null;
  rouletteTarget: string | null;
  // Set by HostView on mount. Host skips the roulette animation and jumps
  // straight to the winner so the operator can re-roll quickly for showmanship.
  isHost: boolean;
  _rouletteTimer: ReturnType<typeof setInterval> | null;
}

export const useGameStore = defineStore("game", {
  state: (): GameStoreState => ({
    initialized: false,
    config: {}, // populated from /api/v1/state on connect
    game_state: "uninitialized",
    teams: [],
    categories: [],
    questions: {},
    ui_state: {
      question: "",
      team: "",
      dailydouble: "",
      message: "",
      "overlay-big": "",
      "overlay-small": "",
      "overlay-question": "",
      "container-header": "",
      "container-footer": "",
    },
    active_question: {},
    messages: [],
    dailydouble_range: { min: 0, max: 0 },
    // null outside DD or before the operator has nudged the wager slider.
    dailydouble_wager: null,
    dailydoubleTrigger: 0,
    socket: null,
    rouletteTarget: null,
    isHost: false,
    _rouletteTimer: null,
  }),

  getters: {
    isInProgress: (s): boolean =>
      s.game_state === "in_round" || s.game_state === "in_final",
    isFinished: (s): boolean => s.game_state === "finished",
    teamByTid:
      (s) =>
      (tid: string): Team | undefined =>
        s.teams.find((t) => t.tid === tid),
    activeQuestionId: (s): string => s.ui_state.question || "",
    selectedTeam: (s): string => s.ui_state.team || "",
    isDailyDouble: (s): boolean =>
      s.ui_state.dailydouble === "enabled" ||
      s.ui_state.dailydouble === "revealed",
    isDailyDoubleRevealed: (s): boolean =>
      s.ui_state.dailydouble === "revealed",
    bigOverlayHtml: (s): string => s.ui_state["overlay-big"] || "",
    questionAnswered:
      (s) =>
      (qid: string): boolean =>
        !!s.questions[qid]?.answered,
  },

  actions: {
    async refresh(): Promise<void> {
      const data = await api.state();
      this.applyServerState(data);
      this.initialized = true;
    },

    applyServerState(data: ServerState): void {
      if (data.config) this.config = { ...this.config, ...data.config };
      if (data.game_state) this.game_state = data.game_state;
      if (data.teams) this.teams = data.teams;
      if (data.categories) this.categories = data.categories;
      if (data.questions) this.questions = data.questions;
      if (data.state) {
        for (const [k, v] of Object.entries(data.state)) {
          if (v !== undefined) this.ui_state[k] = v;
        }
      }
      if (data.active_question !== undefined)
        this.active_question = data.active_question || {};
      if (data.messages) this.messages = data.messages;
      if (data.dailydouble_range)
        this.dailydouble_range = data.dailydouble_range;
      if (data.dailydouble_wager !== undefined)
        this.dailydouble_wager = data.dailydouble_wager;
    },

    connectSocket(): void {
      if (this.socket) return;
      const s = getSocket();
      this.socket = s;

      s.on("connect", () => {
        // no-op, state is already loaded via REST
      });

      s.on("state", (data: ServerState) => this.applyServerState(data));

      s.on("question-show", (data: QuestionShowEvent) => {
        this.active_question = {
          text: data.text,
          category: data.category,
          dailydouble: data.dailydouble,
        };
        this.ui_state.question = data.qid;
        this.ui_state.dailydouble = data.dailydouble ? "enabled" : "";
      });

      s.on("question-hide", () => {
        this.active_question = {};
        this.ui_state.question = "";
        this.ui_state.dailydouble = "";
        this.dailydouble_wager = null;
      });

      s.on("dailydouble", (data: DailyDoubleEvent) => {
        this.ui_state.question = data.qid;
        this.ui_state.dailydouble = "enabled";
        this.active_question = { category: data.category, dailydouble: true };
        if (data.team) this.ui_state.team = data.team;
        if (data.range) this.dailydouble_range = data.range;
        this.dailydouble_wager = null;
        this.dailydoubleTrigger += 1;
      });

      s.on("dailydouble-reveal", (data: DailyDoubleRevealEvent) => {
        this.ui_state.dailydouble = "revealed";
        this.active_question = {
          ...this.active_question,
          text: data.text,
          category: data.category,
          dailydouble: true,
        };
        this.ui_state.question = data.qid;
      });

      s.on("dailydouble-range", (data: DailyDoubleRangeEvent) => {
        if (data?.range) this.dailydouble_range = data.range;
      });

      s.on("dailydouble-wager", (data: DailyDoubleWagerEvent) => {
        this.dailydouble_wager =
          data && data.team != null && data.amount != null
            ? { team: data.team, amount: data.amount }
            : null;
      });

      s.on("board-update", (data: BoardUpdateEvent) => {
        this.questions = { ...this.questions, ...data.questions };
        if (data.teams) this.teams = data.teams;
      });

      s.on("team-select", (data: TeamSelectEvent) => {
        this.ui_state.team = data.tid ?? "";
      });

      s.on("team-roulette", (data: TeamRouletteEvent) => {
        this.runRoulette(data.sequence);
      });

      s.on("team-names", (data: TeamNamesEvent) => {
        for (const [tid, name] of Object.entries(data.names)) {
          const t = this.teamByTid(tid);
          if (t) t.name = name;
        }
      });

      s.on("overlay-big", (data: OverlayBigEvent) => {
        this.ui_state["overlay-big"] = data.html || "";
        this.ui_state.message = data.id || "";
      });

      s.on("slider", (data: SliderEvent) => {
        this.ui_state[data.id] = String(data.value);
      });

      s.on("redirect", (data: RedirectEvent) => {
        // game was reset; reload to land on the right view
        if (data?.url) {
          window.location.href = data.url;
        } else {
          window.location.reload();
        }
      });

      s.connect();
    },

    runRoulette(sequence: string[]): void {
      if (!sequence || sequence.length === 0) return;
      // Clear any pending roulette first.
      if (this._rouletteTimer) clearInterval(this._rouletteTimer);
      if (this.isHost) {
        this.ui_state.team = sequence[sequence.length - 1] ?? "";
        return;
      }
      const queue = [...sequence];
      this._rouletteTimer = setInterval(() => {
        if (queue.length === 0) {
          if (this._rouletteTimer) clearInterval(this._rouletteTimer);
          this._rouletteTimer = null;
          return;
        }
        this.ui_state.team = queue.shift() ?? "";
      }, 100);
    },
  },
});
