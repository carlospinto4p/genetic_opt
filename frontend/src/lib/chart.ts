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

/** The `d` of an SVG path through the points, in order. */
export function linePath(points: [number, number][]): string {
  return points.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join('')
}
