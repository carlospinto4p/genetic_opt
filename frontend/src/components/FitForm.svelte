<script lang="ts">
  import type { FitParams } from '../lib/api'
  import { type NumberParam, paramLabels } from '../lib/params'

  // The fields of `FitConfig`, and the two seeds of the algorithm
  let {
    params = $bindable(),
    limits,
  }: {
    params: FitParams
    limits: { n_generations: number; population_size: number }
  } = $props()

  type NumberField = {
    key: NumberParam
    label: string
    help: string
    min: number
    max?: number
    step: number
  }

  let fields: NumberField[] = $derived([
    {
      key: 'population_size',
      label: paramLabels.population_size,
      help: 'Chromosomes in each generation.',
      min: 1,
      max: limits.population_size,
      step: 1,
    },
    {
      key: 'n_generations',
      label: paramLabels.n_generations,
      help: 'Generations bred after the first one, at most.',
      min: 0,
      max: limits.n_generations,
      step: 1,
    },
    {
      key: 'crossovers_prop',
      label: paramLabels.crossovers_prop,
      help: 'Share of the population picked as parents.',
      min: 0,
      max: 1,
      step: 0.05,
    },
    {
      key: 'besties_prop',
      label: paramLabels.besties_prop,
      help: 'Share of parents taken from the top. The rest are random.',
      min: 0,
      max: 1,
      step: 0.05,
    },
    {
      key: 'mutate_prob',
      label: paramLabels.mutate_prob,
      help: 'Chance that a gene of a child is drawn again.',
      min: 0,
      max: 1,
      step: 0.01,
    },
    {
      key: 'min_population_size',
      label: paramLabels.min_population_size,
      help: 'Stop when fewer different chromosomes are left.',
      min: 0,
      step: 1,
    },
    {
      key: 'random_seed',
      label: paramLabels.random_seed,
      help: 'Picks parents, cut points and which genes mutate.',
      min: 0,
      step: 1,
    },
    {
      key: 'gene_space_random_seed',
      label: paramLabels.gene_space_random_seed,
      help: 'Draws the genes of the first population and the mutations.',
      min: 0,
      step: 1,
    },
  ])
</script>

<div class="form">
  {#each fields as f (f.key)}
    <label>
      <span class="label">{f.label}</span>
      <input
        type="number"
        min={f.min}
        max={f.max}
        step={f.step}
        bind:value={params[f.key]}
      />
      <span class="help">{f.help}</span>
    </label>
  {/each}
  <label class="check">
    <input type="checkbox" bind:checked={params.stop_without_improvement} />
    <span>
      <span class="label">Stop when the mean stalls</span>
      <span class="help">
        Stop when the mean score equals the one of the generation before.
      </span>
    </span>
  </label>
</div>

<style>
  .form {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.9rem 1.2rem;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .label {
    font-weight: 600;
  }
  .help {
    color: var(--text-2);
  }
  .check {
    flex-direction: row;
    align-items: flex-start;
    gap: 0.6rem;
  }
  .check input {
    margin-top: 0.4rem;
    width: 1.1rem;
    height: 1.1rem;
  }
  .check > span {
    display: flex;
    flex-direction: column;
  }
</style>
