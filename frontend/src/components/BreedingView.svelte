<script lang="ts" generics="D">
  import type { Breeding, Child, Member } from '../lib/api'
  import { crossedGenes, geneOrigins, parentAt, type Parent } from '../lib/breeding'
  import { fmt } from '../lib/format'
  import GeneStrip from './GeneStrip.svelte'

  // How one generation was made from the one before it, `previous`
  let {
    breeding,
    previous,
    populationSize,
    off = () => [],
  }: {
    breeding: Breeding<D>
    previous: Member<D>[]
    populationSize: number
    off?: (c: Parent<D> | Child<D>) => number[]
  } = $props()

  const SHOWN = 4
  let showAll = $state(false)

  let n_random = $derived(breeding.n_crossovers - breeding.n_besties)
  let pairs = $derived(showAll ? breeding.pairs : breeding.pairs.slice(0, SHOWN))
  let children = $derived(breeding.pairs.flatMap((p) => p.children))
  let stayed = $derived(children.filter((c) => c.stayed).length)
  let changedGenes = $derived(children.reduce((n, c) => n + c.changed.length, 0))

  // How many times each rank of the last generation was picked
  let picks = $derived.by(() => {
    const counts = Array<number>(populationSize).fill(0)
    for (const rank of breeding.parents) counts[rank] += 1
    return counts
  })
</script>

{#if breeding.n_crossovers === 0}
  <p>
    The crossover share picks no parents at this population size, so this
    generation is the same as the one before.
  </p>
{:else}
  <h3>1. Pick the parents</h3>
  <p>
    {breeding.n_crossovers} parents: the {breeding.n_besties} best of the last
    generation, and {n_random} drawn at random from the rest. A random one can
    be drawn twice. They are shuffled, then paired in order.
  </p>
  <div class="ranks" aria-label="Ranks of the last generation picked as parents">
    {#each picks as count, rank (rank)}
      <span
        class="rank"
        class:best={count && rank < breeding.n_besties}
        class:random={count && rank >= breeding.n_besties}
        title={`rank ${rank + 1}: picked ${count} time${count === 1 ? '' : 's'}`}
      >
        {#if count > 1}{count}{/if}
      </span>
    {/each}
  </div>
  <div class="key">
    <span><i class="sw best"></i>picked from the best</span>
    <span><i class="sw random"></i>picked at random</span>
    <span><i class="sw"></i>not picked</span>
    <span class="muted">Rank 1 on the left.</span>
  </div>

  <h3>2. Cross each pair, then mutate the children</h3>
  <p>
    Each pair is cut at one random point. A child takes the genes before the cut
    from one parent and the rest from the other. Then each gene of a child is
    drawn again with the mutation probability. A redrawn gene can come out the
    same, so only the changed ones are marked. This generation, the mutation
    changed {changedGenes} genes over {children.length} children.
  </p>
  <div class="key">
    <span><i class="bar a"></i>from parent A</span>
    <span><i class="bar b"></i>from parent B</span>
    <span><i class="bar both"></i>both parents have it</span>
    <span><i class="ring"></i>changed by the mutation</span>
  </div>

  {#each pairs as pair, i (i)}
    {@const a = parentAt(breeding, previous, pair.a)}
    {@const b = parentAt(breeding, previous, pair.b)}
    <div class="pair card">
      <div class="parents">
        {#each [['A', a], ['B', b]] as const as [name, p] (name)}
          <div class="row">
            <span class="who">Parent {name}</span>
            <GeneStrip genes={p.genes} off={off(p)} />
            <span class="meta">
              score {fmt(p.score)} · rank {p.rank + 1}
              <span class="chip">{p.kind === 'best' ? 'best' : 'random'}</span>
            </span>
          </div>
        {/each}
      </div>
      <div class="children">
        {#each pair.children as child, j (j)}
          {@const crossed = crossedGenes(child)}
          <div class="child">
            <div class="row">
              <span class="who">Child {j + 1}, crossed</span>
              <GeneStrip genes={crossed} origins={geneOrigins(crossed, a.genes, b.genes)} />
            </div>
            <div class="row">
              <span class="who">Child {j + 1}, mutated</span>
              <GeneStrip genes={child.genes} changed={child.changed} off={off(child)} />
              <span class="meta">
                score {fmt(child.score)}
                <span class="chip" class:stayed={child.stayed}>
                  {child.stayed ? 'stayed' : 'dropped'}
                </span>
              </span>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/each}
  {#if breeding.pairs.length > SHOWN}
    <button onclick={() => (showAll = !showAll)}>
      {showAll ? `Show the first ${SHOWN} pairs` : `Show all ${breeding.pairs.length} pairs`}
    </button>
  {/if}

  <h3>3. Keep the best</h3>
  <p>
    The {children.length} children join the {populationSize} chromosomes of the last
    generation. All {children.length + populationSize} are sorted by score and the
    best {populationSize} stay. {stayed} children came in and {stayed} older chromosomes
    left. The best chromosome is never lost this way.
  </p>
{/if}

<style>
  .ranks {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    margin: 0.4rem 0;
  }
  .rank {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    background: var(--bg-raised);
    border: 1px solid var(--grid);
    font-size: 0.7rem;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
  }
  .rank.best {
    background: var(--s1);
    border-color: var(--s1);
  }
  .rank.random {
    background: var(--s2);
    border-color: var(--s2);
  }
  .key {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1.2rem;
    color: var(--text-2);
    margin-bottom: 0.8rem;
  }
  .key i {
    display: inline-block;
    vertical-align: middle;
    margin-right: 0.4rem;
  }
  .sw {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    background: var(--bg-raised);
    border: 1px solid var(--grid);
  }
  .sw.best {
    background: var(--s1);
    border-color: var(--s1);
  }
  .sw.random {
    background: var(--s2);
    border-color: var(--s2);
  }
  .bar {
    width: 18px;
    height: 4px;
    border-radius: 2px;
  }
  .bar.a {
    background: var(--s1);
  }
  .bar.b {
    background: var(--s2);
  }
  .bar.both {
    background: var(--axis);
  }
  .ring {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    outline: 3px solid var(--s7);
    outline-offset: 1px;
    margin-left: 4px;
  }
  .pair {
    margin-bottom: 0.8rem;
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.6rem;
  }
  .children {
    display: grid;
    gap: 0.6rem;
    border-top: 1px dashed var(--grid);
    padding-top: 0.6rem;
  }
  .row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem 0.9rem;
    min-width: 0;
  }
  .pair {
    min-width: 0;
  }
  .who {
    width: 10.5rem;
    color: var(--text-2);
    flex-shrink: 0;
  }
  .meta {
    color: var(--text-2);
    font-variant-numeric: tabular-nums;
  }
  .chip.stayed {
    background: var(--accent-dim);
    color: var(--accent);
  }
</style>
