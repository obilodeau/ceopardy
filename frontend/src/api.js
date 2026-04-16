// Thin REST client for the Flask back-end. Everything funnels through here
// so we have a single place to add auth, retries, or error handling.

const BASE = '/api/v1'

async function request(path, { method = 'GET', body } = {}) {
  const opts = {
    method,
    headers: { Accept: 'application/json' },
  }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}${path}`, opts)
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const msg = data?.error ?? res.statusText
    throw new Error(msg)
  }
  return data
}

export const api = {
  state: () => request('/state'),
  roundfiles: () => request('/roundfiles'),

  init: (payload) => request('/init', { method: 'POST', body: payload }),
  updateTeams: (names) => request('/teams', { method: 'POST', body: names }),

  selectQuestion: (id) =>
    request('/question/select', { method: 'POST', body: { id } }),
  deselectQuestion: () =>
    request('/question/deselect', { method: 'POST' }),
  submitAnswer: (payload) =>
    request('/answer', { method: 'POST', body: payload }),

  selectTeam: (tid) =>
    request('/team/select', { method: 'POST', body: { tid } }),
  roulette: () => request('/team/roulette', { method: 'POST' }),

  showMessage: (id, text) =>
    request('/message/show', { method: 'POST', body: { id, text } }),
  hideMessage: () => request('/message/hide', { method: 'POST' }),

  finish: () => request('/finish', { method: 'POST' }),

  setSliderState: (id, value) =>
    request('/slider', { method: 'POST', body: { id, value } }),
}
