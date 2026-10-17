<script lang="ts">
  import FitForm from '../components/FitForm.svelte'
  import FunctionPlot from '../components/FunctionPlot.svelte'
  import GeneStrip from '../components/GeneStrip.svelte'
  import RunView from '../components/RunView.svelte'
  import ServerError from '../components/ServerError.svelte'
  import { runFunction } from '../lib/api'
  import { fmt } from '../lib/format'
  import { loadExamples, resetLab, runLab, store } from '../lib/store.svelte'

  loadExamples()

  let lab = store.fn
</script>

<h1>Find the highest point of a curve</h1>
<p>
  The function is <code>f(x) = x · sin(10πx) + 1</code>. It has many peaks, higher
  the further <code>x</code> is from 0. A search that only climbs from where it
  starts ends on the nearest peak. Here the population spreads over the whole
  interval and has to find the highest one.
</p>

<div class="card explain">
  <h3>How a chromosome stands for a number</h3>
  <p>
    A chromosome is a list of bits, read as a whole number: the first gene is the
    highest bit. That number is stretched over the interval, so all zeros is the
    lowest <code>x</code> and all ones is the highest. With 16 bits there are 65,536
    points to choose from. The score is <code>f(x)</code>.
  </p>
  <p class="muted">
    A change in the first gene moves <code>x</code> by half the interval. A change in
    the last one barely moves it. The same mutation can be a big jump or a tiny
    step, depending on where it falls.
  </p>
</div>

{#if store.examplesError}
  <ServerError error={store.examplesError} />
{:else if lab.problem && store.examples}
  <h2>The problem</h2>
  <div class="card">
    <div class="interval">
      <label>
        <b>Lowest x</b>
        <input type="number" step="0.5" bind:value={lab.problem.low} />
      </label>
      <label>
        <b>Highest x</b>
        <input type="number" step="0.5" bind:value={lab.problem.high} />
      </label>
      <label>
        <b>Bits per chromosome</b>
        <input
          type="number"
          min="2"
          max={store.examples.limits.genes}
          bind:value={lab.problem.n_bits}
        />
      </label>
      <button onclick={() => resetLab(lab, store.examples!.function)}>
        Back to the defaults
      </button>
    </div>
    <h3>Parameters of the run</h3>
    <FitForm bind:params={lab.problem.fit} limits={store.examples.limits} />
    <div class="actions">
      <button class="primary" disabled={lab.running} onclick={() => runLab(lab, runFunction)}>
        {lab.running ? 'Running…' : 'Run the algorithm'}
      </button>
      {#if lab.error}<span class="error">{lab.error}</span>{/if}
    </div>
  </div>

  {#if lab.run && lab.ran}
    {@const ran = lab.ran}
    {@const curve = lab.run.curve ?? []}
    <h2>The run</h2>
    <RunView run={lab.run} params={ran.fit} decodedLabel="x">
      {#snippet problem(generation)}
        {@const best = generation.population[0]}
        {@const number = parseInt(best.genes.join(''), 2)}
        <div class="card">
          <h3>The population on the curve</h3>
          <FunctionPlot {curve} population={generation.population} />
          <h3>Reading the best chromosome</h3>
          <GeneStrip genes={best.genes} size={24} />
          <p class="reading">
            bits <code>{best.genes.join('')}</code> → number {fmt(number)} of
            {fmt(2 ** ran.n_bits - 1)} → x = {fmt(ran.low)} + ({fmt(ran.high)} −
            {fmt(ran.low)}) × {fmt(number)} / {fmt(2 ** ran.n_bits - 1)} =
            <b>{fmt(best.decoded, 6)}</b> → f(x) = <b>{fmt(best.score, 6)}</b>
          </p>
        </div>
      {/snippet}
      {#snippet decoded(member)}
        {fmt(member.decoded, 6)}
      {/snippet}
    </RunView>
  {/if}
{:else}
  <p class="muted">Loading the example…</p>
{/if}

<style>
  .interval {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: flex-end;
  }
  .interval label {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    width: 12rem;
  }
  .reading {
    margin-top: 0.4rem;
    font-variant-numeric: tabular-nums;
  }
</style>
