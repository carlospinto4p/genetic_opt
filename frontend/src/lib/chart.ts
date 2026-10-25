/** Space left around the plot of a chart, in pixels. */
export interface Pad {
  l: number
  r: number
  t: number
  b: number
}

/** Width and height of the plot inside a chart of `width` by `height`. */
export function plotSize(
  width: number,
  height: number,
  pad: Pad,
): { w: number; h: number } {
  return { w: Math.max(10, width - pad.l - pad.r), h: height - pad.t - pad.b }
}

/**
 * The pixel of a value, with `lo` at `start` and `hi` at `start + length`.
 * A negative `length` draws upwards, as the y axis of an SVG goes down.
 * When `lo` equals `hi`, every value is at `start`.
 */
export function linearScale(
  lo: number,
  hi: number,
  start: number,
  length: number,
): (v: number) => number {
  const span = hi - lo || 1
  return (v) => start + ((v - lo) / span) * length
}

/**
 * The `d` of an SVG path through the points, in order. A `null` point
 * is a gap: the line stops there and starts again at the next one.
 */
export function linePath(points: ([number, number] | null)[]): string {
  return points
    .map((p, i) => (p ? `${points[i - 1] ? 'L' : 'M'}${p[0]},${p[1]}` : ''))
    .join('')
}

/**
 * The indices of the values with no value on either side, which a line
 * cannot draw: a series of one, or one between two gaps.
 */
export function lonePoints(values: (number | null)[]): number[] {
  return values.flatMap((v, i) =>
    v !== null && (values[i - 1] ?? null) === null && (values[i + 1] ?? null) === null
      ? [i]
      : [],
  )
}
