<script lang="ts" generics="D">
  import type { Snippet } from 'svelte'
  import type { Child, FitParams, Generation, Member, Parent, Run } from '../lib/api'
  import { fmt, pct } from '../lib/format'
  import BreedingView from './BreedingView.svelte'
  import LineChart from './LineChart.svelte'
  import PopulationTable from './PopulationTable.svelte'

  // A recorded run: what it found, its curves, and each generation
  let {
    run,
    params,
    problem,
    decoded,
    decodedLabel,
    off = () => [],
  }: {
    run: Run<D>
    params: FitParams
    problem: Snippet<[Generation<D>, number]>
    decoded: Snippet<[Member<D>]>
    decodedLabel: string
    off?: (c: Member<D> | Parent<D> | Child<D>) => number[]
  } = $props()

  let index = $state(0)
  let playing = $state(false)
  let tab = $state<'breeding' | 'population'>('breeding')

  let last = $derived(run.generations.length - 1)
  let generation = $derived(run.generations[Math.min(index, last)])

  $effect(() => {
    // A new run starts on its last generation
    void run
    index = run.generations.length - 1
    playing = false
  })

  $effect(() => {
    if (!playing) return
    const timer = setInterval(() => {
      if (index >= last) playing = false
      else index += 1
    }, 700)
    return () => clearInterval(timer)
  })

  function play() {
    if (index >= last) index = 0
    playing = !playing
  }

  let stopText = $derived.by(() => {
    if (run.stop_reason === 'completed') return `It ran all ${last} generations.`
    if (run.stop_reason === 'min_population') {
      return (
        `It stopped at generation ${last}: fewer than ` +
        `${params.min_population_size} different chromosomes were left.`
      )
    }
    return (
      `It stopped at generation ${last}: the mean score was the same as in ` +
      `the generation before.`
    )
  })

  let metrics = $derived(run.generations.map((g) => g.metrics))
  let calls = $derived(run.fit_metrics)
</script>

<section class="summary">
  <div class="tile card">
    <div class="tile-label">Best score</div>
    <div class="tile-value">{fmt(metrics[last].best)}</div>
    <div class="muted">at the last generation</div>
  </div>
  <div class="tile card">
    <div class="tile-label">Generations</div>
    <div class="tile-value">{last}</div>
    <div class="muted">after the random start</div>
  </div>
  <div class="tile card">
    <div class="tile-label">Fitness calls</div>
    <div class="tile-value">{calls.processed}</div>
    <div class="muted">
      scored, of {calls.total} asked. {calls.cached} were chromosomes seen before,
      read from the cache.
    </div>
  </div>
  <div class="tile card">
    <div class="tile-label">Search space seen</div>
    <div class="tile-value">{pct(calls.exploration_percentage)}</div>
    <div class="muted">
      {calls.processed} of {fmt(calls.space_points)} possible chromosomes.
    </div>
  </div>
</section>
<p class="stop">{stopText}</p>

<section class="charts">
  <div class="card">
    <h3>Score by generation</h3>
    <LineChart
      series={[
        { name: 'best', color: 'var(--s1)', values: metrics.map((m) => m.best) },
        { name: 'mean', color: 'var(--s2)', values: metrics.map((m) => m.mean) },
        { name: 'median', color: 'var(--s3)', values: metrics.map((m) => m.median) },
      ]}
      selected={index}
      onselect={(i) => {
        playing = false
        index = i
      }}
    />
  </div>
  <div class="card">
    <h3>Different chromosomes, % of the population</h3>
    <LineChart
      series={[
        {
          name: 'different',
          color: 'var(--s1)',
          values: metrics.map((m) => m.percent_uniques),
        },
      ]}
      yMin={0}
      yMax={100}
      format={(v) => `${fmt(v, 3)}%`}
      selected={index}
      onselect={(i) => {
        playing = false
        index = i
      }}
    />
  </div>
</section>

<section class="player card">
  <button class="primary" onclick={play}>{playing ? 'Pause' : 'Play'}</button>
  <button disabled={index === 0} onclick={() => (index -= 1)} aria-label="Previous generation">‹</button>
  <input
    type="range"
    min="0"
    max={last}
    bind:value={index}
    oninput={() => (playing = false)}
    aria-label="Generation"
  />
  <button disabled={index === last} onclick={() => (index += 1)} aria-label="Next generation">›</button>
  <span class="gen">Generation <b>{index}</b> of {last}</span>
</section>

<section class="problem">
  {@render problem(generation, index)}
</section>

<div class="tabs" role="tablist">
  <button
    role="tab"
    aria-selected={tab === 'breeding'}
    class:active={tab === 'breeding'}
    onclick={() => (tab = 'breeding')}
  >
    How generation {index} was made
  </button>
  <button
    role="tab"
    aria-selected={tab === 'population'}
    class:active={tab === 'population'}
    onclick={() => (tab = 'population')}
  >
    Its population ({generation.population.length})
  </button>
</div>

<section class="card">
  {#if tab === 'population'}
    <PopulationTable population={generation.population} {decoded} {decodedLabel} {off} />
  {:else if generation.breeding}
    <BreedingView
      breeding={generation.breeding}
      populationSize={generation.population.length}
      {off}
    />
  {:else}
    <p>
      Generation 0 has no parents. Each of its {generation.population.length}
      chromosomes gets {run.chromosome_length} genes drawn at random from the gene
      space. Then each one is scored and the population is sorted, best first.
    </p>
  {/if}
</section>

<style>
  .summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.8rem;
  }
  .tile-label {
    color: var(--text-2);
    font-weight: 600;
  }
  .tile-value {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .stop {
    margin: 0.8rem 0 1.2rem;
    font-weight: 600;
  }
  .charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr));
    gap: 0.8rem;
  }
  .charts h3 {
    margin-top: 0;
  }
  /* So a chart can shrink below the width it was first drawn at */
  .charts > .card,
  .problem {
    min-width: 0;
  }
  .player {
    position: sticky;
    top: 0;
    z-index: 3;
    margin: 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  .player input {
    flex: 1;
    min-width: 0;
  }
  .gen {
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .problem {
    margin-bottom: 1rem;
  }
  .tabs {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
  }
  .tabs button.active {
    background: var(--accent-dim);
    color: var(--accent);
    border-color: var(--accent-dim);
    font-weight: 600;
  }
  @media (max-width: 700px) {
    .charts {
      grid-template-columns: 1fr;
    }
    .player {
      flex-wrap: wrap;
    }
    .player input {
      order: 5;
      flex-basis: 100%;
    }
  }
</style>
