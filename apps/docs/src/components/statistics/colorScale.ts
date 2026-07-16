/** Shared percentile-based color scale for statistics charts. */

const CRITICAL: [number, number, number] = [0xe7, 0x4c, 0x3c];
const WARNING: [number, number, number] = [0xf5, 0xa6, 0x23];
const GOOD: [number, number, number] = [0x50, 0xc8, 0x78];

/** Percentile rank (0-100) of `value` within `values`, using mid-rank for ties. */
export function percentileRank(value: number, values: number[]): number {
  if (values.length === 0) return 0;

  let below = 0;
  let equal = 0;
  for (const v of values) {
    if (v < value) below++;
    else if (v === value) equal++;
  }
  return ((below + equal / 2) / values.length) * 100;
}

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t);
}

function rgbToHex([r, g, b]: [number, number, number]): string {
  return `#${[r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('')}`;
}

/** Maps a percentile (0-100) to a color on a red -> amber -> green gradient. */
export function percentileToColor(percentile: number): string {
  const p = Math.max(0, Math.min(100, percentile));
  const [from, to, t] =
    p <= 50 ? [CRITICAL, WARNING, p / 50] : [WARNING, GOOD, (p - 50) / 50];

  return rgbToHex([lerp(from[0], to[0], t), lerp(from[1], to[1], t), lerp(from[2], to[2], t)]);
}
