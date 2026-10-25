<script lang="ts">
  import { linePath, linearScale, lonePoints, plotSize } from '../lib/chart'
  import { fmt, niceTicks } from '../lib/format'

  // Values per generation, one line per series, on one axis. A
  // click picks a generation; `selected` draws it as a vertical line.
  // A `null` value, too large for a float, is a gap in the line.
  interface Series {
    name: string
    color: string
    values: (number | null)[]
  }

  let {
    series,
    selected = -1,
    onselect,
    height = 240,
    format = (v: number) => fmt(v),
    yMin = undefined,
    yMax = undefined,
  }: {
    series: Series[]
    selected?: number
    onselect?: (i: number) => void
    height?: number
    format?: (v: number) => string
    yMin?: number
    yMax?: number
  } = $props()

  let width = $state(600)
  let hover = $state(-1)

  let n = $derived(series[0]?.values.length ?? 0)
  let ticks = $derived.by(() => {
    const all = series.flatMap((s) => s.values.filter((v) => v !== null))
    return niceTicks(yMin ?? Math.min(...all), yMax ?? Math.max(...all))
  })
  // The left side fits the longest tick label, such as 0.000036
  let pad = $derived({
    l: Math.max(60, 16 + 8 * Math.max(...ticks.map((t) => format(t).length))),
    r: 90,
    t: 14,
    b: 32,
  })
  let size = $derived(plotSize(width, height, pad))
  let plotW = $derived(size.w)
  let plotH = $derived(size.h)

  // One generation alone sits in the middle
  let x = $derived(
    n <= 1 ? () => pad.l + plotW / 2 : linearScale(0, n - 1, pad.l, plotW),
  )
  let y = $derived(
    linearScale(ticks[0], ticks[ticks.length - 1], pad.t + plotH, -plotH),
  )

  let xTicks = $derived.by(() => {
    if (n <= 1) return [0]
    return niceTicks(0, n - 1, Math.min(8, n - 1)).filter(
      (t) => Number.isInteger(t) && t <= n - 1,
    )
  })

  // Labels at the end of each line, pushed apart so they do not overlap.
  // A line ending in a gap is labelled at its last value.
  let endLabels = $derived.by(() => {
    const labels = series
      .flatMap((s) => {
        const last = s.values.filter((v) => v !== null).at(-1)
        return last === undefined ? [] : [{ name: s.name, color: s.color, y: y(last) }]
      })
      .sort((a, b) => a.y - b.y)
    for (let i = 1; i < labels.length; i++) {
      labels[i].y = Math.max(labels[i].y, labels[i - 1].y + 17)
    }
    return labels
  })

  function path(values: (number | null)[]): string {
    return linePath(values.map((v, i) => (v === null ? null : [x(i), y(v)])))
  }

  function label(v: number | null): string {
    return v === null ? 'too large' : format(v)
  }

  function indexAt(e: MouseEvent): number {
    const rect = (e.currentTarget as SVGElement).getBoundingClientRect()
    const px = e.clientX - rect.left - pad.l
    if (n <= 1) return 0
    return Math.max(0, Math.min(n - 1, Math.round((px / plotW) * (n - 1))))
  }
</script>

<div class="chart" bind:clientWidth={width}>
  {#if series.length > 1}
    <div class="legend">
      {#each series as s (s.name)}
        <span><i style="background: {s.color}"></i>{s.name}</span>
      {/each}
    </div>
  {/if}
  <svg
    {width}
    {height}
    role="button"
    tabindex="0"
    aria-label="Chart by generation. Click to pick a generation."
    onmousemove={(e) => (hover = indexAt(e))}
    onmouseleave={() => (hover = -1)}
    onclick={(e) => onselect?.(indexAt(e))}
    onkeydown={(e) => {
      if (e.key === 'ArrowRight') onselect?.(Math.min(n - 1, selected + 1))
      if (e.key === 'ArrowLeft') onselect?.(Math.max(0, selected - 1))
    }}
  >
    {#each ticks as t (t)}
      <line class="grid" x1={pad.l} x2={pad.l + plotW} y1={y(t)} y2={y(t)} />
      <text class="tick" x={pad.l - 8} y={y(t) + 5} text-anchor="end">
        {format(t)}
      </text>
    {/each}
    <line
      class="axis"
      x1={pad.l}
      x2={pad.l + plotW}
      y1={pad.t + plotH}
      y2={pad.t + plotH}
    />
    {#each xTicks as t (t)}
      <text class="tick" x={x(t)} y={height - 8} text-anchor="middle">{t}</text>
    {/each}

    {#if selected >= 0 && selected < n}
      <line
        class="selected"
        x1={x(selected)}
        x2={x(selected)}
        y1={pad.t}
        y2={pad.t + plotH}
      />
    {/if}

    {#each series as s (s.name)}
      <path d={path(s.values)} fill="none" stroke={s.color} stroke-width="2" />
      {#each lonePoints(s.values) as i (i)}
        <circle cx={x(i)} cy={y(s.values[i]!)} r="4" fill={s.color} />
      {/each}
    {/each}

    {#each endLabels as l (l.name)}
      <text class="end-label" x={pad.l + plotW + 8} y={l.y + 5}>{l.name}</text>
    {/each}

    {#if hover >= 0}
      <line
        class="crosshair"
        x1={x(hover)}
        x2={x(hover)}
        y1={pad.t}
        y2={pad.t + plotH}
      />
      {#each series.filter((s) => s.values[hover] !== null) as s (s.name)}
        <circle
          cx={x(hover)}
          cy={y(s.values[hover]!)}
          r="4.5"
          fill={s.color}
          stroke="var(--bg-surface)"
          stroke-width="2"
        />
      {/each}
    {/if}
  </svg>
  {#if hover >= 0}
    <div
      class="tooltip"
      style="left: {Math.min(x(hover) + 12, width - 170)}px; top: {pad.t}px"
    >
      <div class="tooltip-title">Generation {hover}</div>
      {#each series as s (s.name)}
        <div class="tooltip-row">
          <i style="background: {s.color}"></i>
          <span>{s.name}</span>
          <b>{label(s.values[hover])}</b>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .chart {
    position: relative;
    width: 100%;
    min-width: 0;
    overflow: hidden;
  }
  svg {
    display: block;
    cursor: crosshair;
  }
  svg:focus-visible {
    outline: 2px solid var(--accent);
    border-radius: 4px;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    color: var(--text-2);
    margin-bottom: 0.3rem;
  }
  .legend i,
  .tooltip i {
    display: inline-block;
    width: 0.8rem;
    height: 3px;
    border-radius: 2px;
    margin-right: 0.4rem;
    vertical-align: middle;
  }
  .grid {
    stroke: var(--grid);
  }
  .axis {
    stroke: var(--axis);
  }
  .tick {
    fill: var(--muted);
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
  }
  .end-label {
    fill: var(--text-2);
    font-size: 0.9rem;
  }
  .selected {
    stroke: var(--accent);
    stroke-width: 2;
    stroke-dasharray: 4 3;
  }
  .crosshair {
    stroke: var(--muted);
  }
  .tooltip {
    position: absolute;
    pointer-events: none;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 0.4rem 0.6rem;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
    min-width: 150px;
  }
  .tooltip-title {
    font-weight: 600;
  }
  .tooltip-row {
    display: flex;
    align-items: center;
    gap: 0.2rem;
    color: var(--text-2);
  }
  .tooltip-row b {
    margin-left: auto;
    padding-left: 0.8rem;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }
</style>
