<script lang="ts">
  import FitForm from '../components/FitForm.svelte'
  import GeneStrip from '../components/GeneStrip.svelte'
  import RunView from '../components/RunView.svelte'
  import ServerError from '../components/ServerError.svelte'
  import { runKnapsack, type Chromosome } from '../lib/api'
  import { fmt } from '../lib/format'
  import { loadExamples, resetLab, runLab, store } from '../lib/store.svelte'

  loadExamples()

  let lab = store.knapsack

  // Genes that ask for an object the decoding leaves out of the bag
  const off = (c: Chromosome<number[]>) =>
    c.genes.flatMap((g, i) => (g === 1 && c.decoded[i] === 0 ? [i] : []))

  function addObject() {
    lab.problem!.weights.push(10)
    lab.problem!.values.push(10)
  }

  function removeObject(i: number) {
    lab.problem!.weights.splice(i, 1)
    lab.problem!.values.splice(i, 1)
  }

  let totalWeight = $derived(
    lab.problem ? lab.problem.weights.reduce((a, b) => a + b, 0) : 0,
  )
</script>

<h1>The knapsack problem</h1>
<p>
  Some objects each have a weight and a value. A bag holds up to a given weight.
  Which objects give the most value without going over? This is the
  <code>Knapsack</code> example of the package, and the defaults are the ones in
  its README.
</p>

<div class="card explain">
  <h3>How a chromosome stands for a bag</h3>
  <p>
    One gene per object: <b>1</b> asks to put it in, <b>0</b> leaves it out. The
    decoding goes through the objects in order and puts in each one asked for. At
    the first one that does not fit, the bag is closed: that object and every later
    one stay out. The score is the total value of the objects in the bag.
  </p>
  <p class="muted">
    So two different chromosomes can stand for the same bag. A crossed-out gene
    below asked for an object that did not fit.
  </p>
</div>

{#if store.examplesError}
  <ServerError error={store.examplesError} />
{:else if lab.problem && store.examples}
  <h2>The problem</h2>
  <div class="setup">
    <div class="card objects-card">
      <table>
        <thead>
          <tr>
            <th class="num">Object</th>
            <th>Weight</th>
            <th>Value</th>
            <th class="num">Value per weight</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each lab.problem.weights as _, i (i)}
            <tr>
              <td class="num">{i + 1}</td>
              <td><input type="number" min="0" bind:value={lab.problem.weights[i]} /></td>
              <td><input type="number" min="0" bind:value={lab.problem.values[i]} /></td>
              <td class="num">
                {lab.problem.weights[i]
                  ? fmt(lab.problem.values[i] / lab.problem.weights[i], 3)
                  : '-'}
              </td>
              <td>
                <button
                  disabled={lab.problem.weights.length <= 1}
                  onclick={() => removeObject(i)}
                  aria-label={`Remove object ${i + 1}`}>✕</button
                >
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
      <div class="actions">
        <button
          disabled={lab.problem.weights.length >= store.examples.limits.genes}
          onclick={addObject}>Add an object</button
        >
        <button onclick={() => resetLab(lab, store.examples!.knapsack)}>
          Back to the README example
        </button>
      </div>
    </div>
    <div class="card">
      <label class="capacity">
        <span><b>Bag capacity</b></span>
        <input type="number" min="0" bind:value={lab.problem.capacity} />
      </label>
      <p class="muted">
        All {lab.problem.weights.length} objects weigh {totalWeight} together. There
        are 2<sup>{lab.problem.weights.length}</sup> =
        {fmt(2 ** lab.problem.weights.length)} possible chromosomes.
      </p>
      <h3>Parameters of the run</h3>
      <FitForm bind:params={lab.problem.fit} limits={store.examples.limits} />
      <div class="actions">
        <button
          class="primary"
          disabled={lab.running}
          onclick={() => runLab(lab, runKnapsack)}
        >
          {lab.running ? 'Running…' : 'Run the algorithm'}
        </button>
        {#if lab.error}<span class="error">{lab.error}</span>{/if}
      </div>
    </div>
  </div>

  {#if lab.run && lab.ran}
    {@const ran = lab.ran}
    <h2>The run</h2>
    <RunView run={lab.run} params={ran.fit} decodedLabel="Bag" {off}>
      {#snippet problem(generation)}
        {@const best = generation.population[0]}
        {@const weight = best.decoded.reduce((s, g, i) => s + g * ran.weights[i], 0)}
        <div class="card">
          <h3>Best bag of this generation</h3>
          <GeneStrip genes={best.genes} off={off(best)} size={28} />
          <div class="objects">
            {#each ran.weights as w, i (i)}
              {@const state =
                best.decoded[i] === 1 ? 'in' : best.genes[i] === 1 ? 'nofit' : 'out'}
              <div class="object {state}">
                <div class="object-name">Object {i + 1}</div>
                <div>weight {w} · value {ran.values[i]}</div>
                <div class="object-state">
                  {state === 'in' ? 'in the bag' : state === 'nofit' ? 'did not fit' : 'left out'}
                </div>
              </div>
            {/each}
          </div>
          <div class="fill" aria-label={`Weight ${weight} of ${ran.capacity}`}>
            <div
              class="fill-bar"
              style="width: {Math.min(100, (100 * weight) / (ran.capacity || 1))}%"
            ></div>
          </div>
          <p class="muted">
            Weight {weight} of {ran.capacity}. Value {fmt(best.score)}.
          </p>
        </div>
      {/snippet}
      {#snippet decoded(member)}
        {@const objects = member.decoded.flatMap((g, i) => (g ? [i + 1] : []))}
        {objects.length ? `objects ${objects.join(', ')}` : 'empty'}
      {/snippet}
    </RunView>
  {/if}
{:else}
  <p class="muted">Loading the example…</p>
{/if}

<style>
  .setup {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
    gap: 0.8rem;
    align-items: start;
  }
  .objects-card {
    overflow-x: auto;
  }
  .setup td input {
    width: 6rem;
  }
  .capacity {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 0.4rem;
  }
  .capacity input {
    width: 8rem;
  }
  .objects {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.5rem;
    margin: 0.8rem 0;
  }
  .object {
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 0.4rem 0.6rem;
    color: var(--text-2);
  }
  .object.in {
    border-color: var(--s1);
    background: var(--accent-dim);
    color: var(--text);
  }
  .object.nofit {
    border-color: var(--critical);
    border-style: dashed;
  }
  .object-name {
    font-weight: 600;
    color: var(--text);
  }
  .object-state {
    font-weight: 600;
  }
  .fill {
    height: 12px;
    border-radius: 6px;
    background: var(--bg-raised);
    overflow: hidden;
  }
  .fill-bar {
    height: 100%;
    background: var(--s1);
  }
  @media (max-width: 900px) {
    .setup {
      grid-template-columns: 1fr;
    }
  }
</style>
