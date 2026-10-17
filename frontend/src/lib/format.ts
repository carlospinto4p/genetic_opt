/** A number with at most `digits` significant digits, without float noise. */
export function fmt(value: number, digits = 4): string {
  if (!Number.isFinite(value)) return String(value)
  if (Number.isInteger(value)) return value.toLocaleString('en')
  return Number(value.toPrecision(digits)).toLocaleString('en', {
    maximumFractionDigits: 6,
  })
}

/** A percentage with one decimal. */
export function pct(value: number): string {
  return `${Number(value.toFixed(1))}%`
}

/** Round tick values covering `[min, max]`. */
export function niceTicks(min: number, max: number, count = 5): number[] {
  if (min === max) {
    min -= 1
    max += 1
  }
  const rough = (max - min) / count
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const ratio = rough / magnitude
  const step =
    (ratio >= 7.5 ? 10 : ratio >= 3.5 ? 5 : ratio >= 1.5 ? 2 : 1) * magnitude
  // Up to the first tick at or over `max`, so every value fits
  const ticks = []
  for (let t = Math.floor(min / step) * step; ; t += step) {
    ticks.push(Number(t.toPrecision(12)))
    if (t >= max) return ticks
  }
}
