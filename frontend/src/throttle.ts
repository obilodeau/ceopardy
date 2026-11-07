// SPDX-License-Identifier: GPL-3.0-or-later

/**
 * Call `fn` at most once every `ms` for a slider being dragged. The first
 * value goes out at once and the last one is never dropped.
 */
export function throttle<T>(
  fn: (value: T) => void,
  ms: number,
): (value: T) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let pending: { value: T } | null = null;

  function run(value: T): void {
    fn(value);
    timer = setTimeout(() => {
      timer = null;
      if (pending) {
        const next = pending.value;
        pending = null;
        run(next);
      }
    }, ms);
  }

  return (value: T): void => {
    if (timer) pending = { value };
    else run(value);
  };
}
