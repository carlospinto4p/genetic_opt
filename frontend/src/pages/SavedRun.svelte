<script lang="ts">
  import RunView from '../components/RunView.svelte'
  import { openSavedRun } from '../lib/api'
  import { fmt } from '../lib/format'
  import { store } from '../lib/store.svelte'

  let saved = store.saved

  async function open(e: SubmitEvent) {
    e.preventDefault()
    const path = saved.path.trim()
    if (!path) return
    saved.loading = true
    saved.error = ''
    try {
      saved.run = await openSavedRun(path)
    } catch (err) {
      saved.error = (err as Error).message
    } finally {
      saved.loading = false
    }
  }

  // The parameters a saved file holds, with the names the forms use
  let parameters = $derived.by(() => {
    if (!saved.run) return []
    const p = saved.run.fit_parameters
    return [
      ['Population size', p.population_size],
      ['Generations asked', p.n_generations],
      ['Crossover share', p.crossovers_prop],
      ['Best parents share', p.besties_prop],
      ['Mutation probability', p.mutate_prob],
      ['Minimum different', p.min_population_size],
      ['Algorithm seed', p.random_seed],
    ] as const
  })
</script>

<h1>Open a saved run</h1>
<p>
  A run saved by <code>fit</code>, or by the Rust crate, is a folder with one file
  per generation in <code>fit_data</code>. Give its path to step through it. The
  files hold each population and its scores, not the parents or the crossovers, so
  this page cannot show how a generation was made.
</p>

<form class="card open" onsubmit={open}>
  <label>
    <span><b>Folder of the run</b></span>
    <input
      type="text"
      bind:value={saved.path}
      placeholder="/path/to/run"
      spellcheck="false"
      autocomplete="off"
    />
  </label>
  <button class="primary" type="submit" disabled={saved.loading || !saved.path.trim()}>
    {saved.loading ? 'Reading the files…' : 'Open'}
  </button>
  <p class="muted">
    The server reads the folder on its own machine. Its <code>fit_data</code> folder
    works too.
  </p>
  {#if saved.error}<p class="error">{saved.error}</p>{/if}
</form>

{#if saved.run}
  {@const run = saved.run}
  <h2>The run</h2>
  <div class="card about">
    <p>
      <code>{run.folder}</code>, saved by genetic_opt {run.genetic_opt_version}.
    </p>
    <dl>
      {#each parameters as [label, value] (label)}
        <div>
          <dt>{label}</dt>
          <dd>{fmt(value)}</dd>
        </div>
      {/each}
    </dl>
  </div>
  <RunView {run} params={run.fit_parameters} />
{/if}

<style>
  .open {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem 0.8rem;
    margin: 1rem 0;
  }
  .open label {
    display: flex;
    flex: 1;
    align-items: center;
    gap: 0.8rem;
    min-width: min(100%, 320px);
  }
  .open input {
    flex: 1;
    min-width: 0;
    font-family: var(--mono);
  }
  .open p {
    flex-basis: 100%;
    margin: 0;
  }
  .about {
    margin-bottom: 1rem;
  }
  .about p {
    margin-top: 0;
    overflow-wrap: anywhere;
  }
  dl {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 0.5rem 1rem;
    margin: 0;
  }
  dt {
    color: var(--text-2);
    font-weight: 600;
  }
  dd {
    margin: 0;
    font-variant-numeric: tabular-nums;
  }
</style>
