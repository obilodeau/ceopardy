// SPDX-License-Identifier: GPL-3.0-or-later

/** 1st, 2nd, 3rd, 4th, ..., 11th, 12th, 13th, ..., 21st. */
export function ordinal(n: number): string {
  const teen = n % 100 >= 11 && n % 100 <= 13;
  const suffix = teen ? "th" : (["th", "st", "nd", "rd"][n % 10] ?? "th");
  return `${n}${suffix}`;
}
