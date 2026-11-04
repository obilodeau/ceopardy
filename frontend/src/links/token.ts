// SPDX-License-Identifier: GPL-3.0-or-later
// The secret in a buzzer or soundboard link rides in the URL fragment, which
// browsers never send to a server. Move it to sessionStorage and out of the
// address bar, so it doesn't show on the user's own screen share; a reload
// still finds it.
export function takeToken(storageKey: string): string {
  const fromHash = window.location.hash.slice(1);
  try {
    if (fromHash) {
      sessionStorage.setItem(storageKey, fromHash);
    } else {
      return sessionStorage.getItem(storageKey) ?? "";
    }
  } catch {
    // Storage blocked: keep the token in the URL so a reload still works.
    return fromHash;
  }
  history.replaceState(null, "", window.location.pathname);
  return fromHash;
}
