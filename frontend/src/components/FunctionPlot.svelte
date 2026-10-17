<script lang="ts">
  import type { Member } from '../lib/api'
  import { fmt, niceTicks } from '../lib/format'

  // The curve of the function, and where each chromosome of a
  // population sits on it
  let {
    curve,
    population,
    height = 300,
  }: { curve: [number, number][]; population: Member<number>[]; height?: number } =
    $props()

  let width = $state(700)
  let hover = $state<Member<number> | null>(null)

  const pad = { l: 52, r: 16, t: 14, b: 32 }

  let xs = $derived(curve.map((p) => p[0]))
  let ys = $derived(curve.map((p) => p[1]))
  let xTicks = $derived(niceTicks(xs[0], xs[xs.length - 1], 6))
  let yTicks = $derived(niceTicks(Math.min(...ys), Math.max(...ys), 5))
  let plotW = $derived(Math.max(10, width - pad.l - pad.r))
  let plotH = $derived(height - pad.t - pad.b)
  let x0 = $derived(xs[0])
  let x1 = $derived(xs[xs.length - 1])
  let y0 = $derived(yTicks[0])
  let y1 = $derived(yTicks[yTicks.length - 1])

  const px = (x: number) => pad.l + ((x - x0) / (x1 - x0)) * plotW
  const py = (y: number) => pad.t + plotH - ((y - y0) / (y1 - y0 || 1)) * plotH

  let line = $derived(curve.map(([x, y], i) => `${i ? 'L' : 'M'}${px(x)},${py(y)}`).join(''))
  // One dot per different chromosome, with how many copies it has
  let dots = $derived.by(() => {
    const seen = new Map<string, { m: Member<number>; copies: number }>()
    for (const m of population) {
      const key = m.genes.join('')
      const dot = seen.get(key)
      if (dot) dot.copies += 1
      else seen.set(key, { m, copies: 1 })
    }
    return [...seen.values()]
  })
  let best = $derived(population[0])
</script>

<div class="plot" bind:clientWidth={width}>
  <div class="legend">
    <span><i class="line"></i>f(x)</span>
    <span><i class="dot"></i>a chromosome of this generation</span>
    <span><i class="dot best"></i>the best one</span>
  </div>
  <svg {width} {height} role="img" aria-label="The function and the population on it">
    {#each yTicks as t (t)}
      <line class="grid" x1={pad.l} x2={pad.l + plotW} y1={py(t)} y2={py(t)} />
      <text class="tick" x={pad.l - 8} y={py(t) + 5} text-anchor="end">{fmt(t)}</text>
    {/each}
    {#each xTicks.filter((t) => t >= x0 && t <= x1) as t (t)}
      <text class="tick" x={px(t)} y={height - 8} text-anchor="middle">{fmt(t)}</text>
    {/each}
    <path d={line} fill="none" stroke="var(--muted)" stroke-width="2" />
    {#each dots as { m, copies } (m.genes.join(''))}
      <circle
        role="presentation"
        cx={px(m.decoded)}
        cy={py(m.score)}
        r={5 + Math.min(5, copies - 1)}
        fill="var(--s1)"
        fill-opacity="0.85"
        stroke="var(--bg-surface)"
        stroke-width="2"
        onmouseenter={() => (hover = m)}
        onmouseleave={() => (hover = null)}
      />
    {/each}
    <circle
      cx={px(best.decoded)}
      cy={py(best.score)}
      r="8"
      fill="var(--s2)"
      stroke="var(--bg-surface)"
      stroke-width="2"
      pointer-events="none"
    />
  </svg>
  {#if hover}
    <div
      class="tooltip"
      style="left: {Math.min(px(hover.decoded) + 12, width - 220)}px; top: {Math.max(
        0,
        py(hover.score) - 70,
      )}px"
    >
      <div><b>x = {fmt(hover.decoded, 6)}</b></div>
      <div>f(x) = {fmt(hover.score, 6)}</div>
      <div class="mono">{hover.genes.join('')}</div>
    </div>
  {/if}
</div>

<style>
  .plot {
    position: relative;
    min-width: 0;
    overflow: hidden;
  }
  svg {
    display: block;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    color: var(--text-2);
  }
  .legend i {
    display: inline-block;
    vertical-align: middle;
    margin-right: 0.4rem;
  }
  .legend .line {
    width: 16px;
    height: 2px;
    background: var(--muted);
  }
  .legend .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--s1);
  }
  .legend .dot.best {
    background: var(--s2);
  }
  .grid {
    stroke: var(--grid);
  }
  .tick {
    fill: var(--muted);
    font-size: 0.85rem;
  }
  .tooltip {
    position: absolute;
    pointer-events: none;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 0.4rem 0.6rem;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
  }
  .mono {
    font-family: var(--mono);
    color: var(--text-2);
  }
</style>
