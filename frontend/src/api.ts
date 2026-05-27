// SPDX-License-Identifier: GPL-3.0-or-later
// Thin REST client for the Flask back-end. Everything funnels through here
// so we have a single place to add auth, retries, or error handling.

import type {
  ApiOk,
  InitPayload,
  SelectQuestionResponse,
  ServerState,
  SubmitAnswerPayload,
} from "@/types";

const BASE = "/api/v1";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
}

async function request<T = unknown>(
  path: string,
  { method = "GET", body }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const opts: RequestInit = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const msg = (data as { error?: string } | null)?.error ?? res.statusText;
    throw new Error(msg);
  }
  return data as T;
}

export const api = {
  state: () => request<ServerState>("/state"),
  roundfiles: () => request<string[]>("/roundfiles"),

  init: (payload: InitPayload) =>
    request<ApiOk>("/init", { method: "POST", body: payload }),
  updateTeams: (names: Record<string, string>) =>
    request<ApiOk>("/teams", { method: "POST", body: names }),

  selectQuestion: (id: string) =>
    request<SelectQuestionResponse>("/question/select", {
      method: "POST",
      body: { id },
    }),
  deselectQuestion: () =>
    request<ApiOk>("/question/deselect", { method: "POST" }),
  submitAnswer: (payload: SubmitAnswerPayload) =>
    request<ApiOk>("/answer", { method: "POST", body: payload }),

  selectTeam: (tid: string) =>
    request<ApiOk>("/team/select", { method: "POST", body: { tid } }),
  roulette: () => request<ApiOk>("/team/roulette", { method: "POST" }),

  setWager: (amount: number) =>
    request<ApiOk>("/dailydouble/wager", {
      method: "POST",
      body: { amount },
    }),
  revealDailyDouble: () =>
    request<ApiOk>("/dailydouble/reveal", { method: "POST" }),

  showMessage: (id: string, text: string) =>
    request<ApiOk>("/message/show", {
      method: "POST",
      body: { id, text },
    }),
  hideMessage: () => request<ApiOk>("/message/hide", { method: "POST" }),

  finish: () => request<ApiOk>("/finish", { method: "POST" }),

  setSliderState: (id: string, value: string | number) =>
    request<ApiOk>("/slider", { method: "POST", body: { id, value } }),
};
