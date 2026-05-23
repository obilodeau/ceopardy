import { defineStore } from "pinia";
import { api } from "@/api";
import { getSocket } from "@/socket";

// Single source of truth for the game state that both the host and viewer
// views read from. Server broadcasts keep this in sync across windows.
export const useGameStore = defineStore("game", {
  state: () => ({
    initialized: false,
    config: {}, // populated from /api/v1/state on connect
    game_state: "uninitialized",
    teams: [], // [{tid, name, score}]
    categories: [], // ['Cat1', ...]
    questions: {}, // { c1q1: { answered: bool, team_scores: {team1: 100} } }
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
    // {team, amount} as the host moves the wager slider during a DD; null
    // outside DD or before the operator has set anything.
    dailydouble_wager: null,
    // Incremented every time the server fires a new daily-double. Lets the
    // viewer trigger the flip animation without watching for state changes
    // that might bounce during reconnects.
    dailydoubleTrigger: 0,
    socket: null,
    rouletteTarget: null,
    // Set by HostView on mount. Host skips the roulette animation and jumps
    // straight to the winner so the operator can re-roll quickly for showmanship.
    isHost: false,
  }),

  getters: {
    isInProgress: (s) =>
      s.game_state === "in_round" || s.game_state === "in_final",
    isFinished: (s) => s.game_state === "finished",
    teamByTid: (s) => (tid) => s.teams.find((t) => t.tid === tid),
    activeQuestionId: (s) => s.ui_state.question || "",
    selectedTeam: (s) => s.ui_state.team || "",
    isDailyDouble: (s) =>
      s.ui_state.dailydouble === "enabled" ||
      s.ui_state.dailydouble === "revealed",
    isDailyDoubleRevealed: (s) => s.ui_state.dailydouble === "revealed",
    bigOverlayHtml: (s) => s.ui_state["overlay-big"] || "",
    questionAnswered: (s) => (qid) => !!s.questions[qid]?.answered,
  },

  actions: {
    async refresh() {
      const data = await api.state();
      this.applyServerState(data);
      this.initialized = true;
    },

    applyServerState(data) {
      if (data.config) this.config = { ...this.config, ...data.config };
      if (data.game_state) this.game_state = data.game_state;
      if (data.teams) this.teams = data.teams;
      if (data.categories) this.categories = data.categories;
      if (data.questions) this.questions = data.questions;
      if (data.state) this.ui_state = { ...this.ui_state, ...data.state };
      if (data.active_question !== undefined)
        this.active_question = data.active_question || {};
      if (data.messages) this.messages = data.messages;
      if (data.dailydouble_range)
        this.dailydouble_range = data.dailydouble_range;
      if (data.dailydouble_wager !== undefined)
        this.dailydouble_wager = data.dailydouble_wager;
    },

    connectSocket() {
      if (this.socket) return;
      const s = getSocket();
      this.socket = s;

      s.on("connect", () => {
        // no-op, state is already loaded via REST
      });

      s.on("state", (data) => this.applyServerState(data));

      s.on("question-show", (data) => {
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

      s.on("dailydouble", (data) => {
        this.ui_state.question = data.qid;
        this.ui_state.dailydouble = "enabled";
        this.active_question = { category: data.category, dailydouble: true };
        if (data.team) this.ui_state.team = data.team;
        if (data.range) this.dailydouble_range = data.range;
        this.dailydouble_wager = null;
        this.dailydoubleTrigger += 1;
      });

      s.on("dailydouble-reveal", (data) => {
        this.ui_state.dailydouble = "revealed";
        this.active_question = {
          ...this.active_question,
          text: data.text,
          category: data.category,
          dailydouble: true,
        };
        this.ui_state.question = data.qid;
      });

      s.on("dailydouble-range", (data) => {
        if (data?.range) this.dailydouble_range = data.range;
      });

      s.on("dailydouble-wager", (data) => {
        this.dailydouble_wager =
          data && data.team != null && data.amount != null
            ? { team: data.team, amount: data.amount }
            : null;
      });

      s.on("board-update", (data) => {
        this.questions = { ...this.questions, ...data.questions };
        if (data.teams) this.teams = data.teams;
      });

      s.on("team-select", (data) => {
        this.ui_state.team = data.tid ?? "";
      });

      s.on("team-roulette", (data) => {
        this.runRoulette(data.sequence);
      });

      s.on("team-names", (data) => {
        for (const [tid, name] of Object.entries(data.names)) {
          const t = this.teamByTid(tid);
          if (t) t.name = name;
        }
      });

      s.on("overlay-big", (data) => {
        this.ui_state["overlay-big"] = data.html || "";
        this.ui_state.message = data.id || "";
      });

      s.on("slider", (data) => {
        this.ui_state[data.id] = data.value;
      });

      s.on("redirect", (data) => {
        // game was reset; reload to land on the right view
        if (data?.url) {
          window.location.href = data.url;
        } else {
          window.location.reload();
        }
      });

      s.connect();
    },

    runRoulette(sequence) {
      if (!sequence || sequence.length === 0) return;
      // Clear any pending roulette first.
      if (this._rouletteTimer) clearInterval(this._rouletteTimer);
      if (this.isHost) {
        this.ui_state.team = sequence[sequence.length - 1];
        return;
      }
      const queue = [...sequence];
      this._rouletteTimer = setInterval(() => {
        if (queue.length === 0) {
          clearInterval(this._rouletteTimer);
          this._rouletteTimer = null;
          return;
        }
        this.ui_state.team = queue.shift();
      }, 100);
    },
  },
});
