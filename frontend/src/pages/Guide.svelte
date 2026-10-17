<script lang="ts">
  import GeneStrip from '../components/GeneStrip.svelte'
  import { runKnapsack, type Gene, type GeneOrigin } from '../lib/api'
  import { crossedGenes, parentAt } from '../lib/breeding'
  import { fmt } from '../lib/format'
  import { loadExamples, runLab, store } from '../lib/store.svelte'

  // Every example on this page comes from one real run of the
  // package's `Knapsack`, with the defaults of the server.
  let lab = store.guide

  loadExamples().then(() => {
    if (!lab.run && !lab.running) runLab(lab, runKnapsack)
  })

  let ran = $derived(lab.ran)
  let run = $derived(lab.run)
  let first = $derived(run?.generations[0].population[0])
  let breeding = $derived(run?.generations[1]?.breeding)
  let pair = $derived(breeding?.pairs[0])
  let parentA = $derived(
    pair && breeding && run ? parentAt(breeding, run.generations[0].population, pair.a) : undefined,
  )
  let parentB = $derived(
    pair && breeding && run ? parentAt(breeding, run.generations[0].population, pair.b) : undefined,
  )
  // A child the mutation changed, to show one
  let mutated = $derived(
    run?.generations
      .flatMap((g) => g.breeding?.pairs.flatMap((p) => p.children) ?? [])
      .find((c) => c.changed.length > 0),
  )

  let length = $derived(ran?.weights.length ?? 10)
  let cut = $state(4)

  function cross(a: Gene[], b: Gene[]) {
    const origins = (start: GeneOrigin, end: GeneOrigin) =>
      a.map((g, i) => (g === b[i] ? 'both' : i < cut ? start : end)) as GeneOrigin[]
    return [
      { genes: [...a.slice(0, cut), ...b.slice(cut)], origins: origins('a', 'b') },
      { genes: [...b.slice(0, cut), ...a.slice(cut)], origins: origins('b', 'a') },
    ]
  }

  let crossed = $derived(parentA && parentB ? cross(parentA.genes, parentB.genes) : [])

  let fit = $derived(ran?.fit)
  let selection = $derived(
    breeding && {
      n: breeding.n_crossovers,
      best: breeding.n_besties,
      random: breeding.n_crossovers - breeding.n_besties,
    },
  )

  const off = (genes: Gene[], decoded: number[]) =>
    genes.flatMap((g, i) => (g === 1 && decoded[i] === 0 ? [i] : []))
</script>

<h1>How a genetic algorithm works</h1>
<p>
  A genetic algorithm searches by breeding. It keeps a population of candidate
  answers, lets the better ones have children, and repeats. Everything on this page
  comes from one real run of the package's Knapsack example: some objects, a bag,
  and the question of which objects to pack for the most value.
</p>

{#if store.examplesError || lab.error}
  <p class="error">
    The server did not answer: {store.examplesError || lab.error}. Start it with
    <code>uv run python -m genetic_opt.web.app</code>.
  </p>
{/if}

<h2>The words</h2>
<div class="terms">
  <div class="card">
    <h3>Gene</h3>
    <p>
      One symbol. In the Knapsack every gene is a 0 or a 1: leave an object out, or
      put it in.
    </p>
  </div>
  <div class="card">
    <h3>Gene space</h3>
    <p>
      Every symbol a gene can take, here <code>{'{0, 1}'}</code>
      (<code>BinaryGeneSpace</code>). New genes are drawn from it at random.
    </p>
  </div>
  <div class="card">
    <h3>Chromosome</h3>
    <p>
      A fixed number of genes: one candidate answer. It is a list, where order
      counts and a gene can repeat, or a set, where it cannot
      (<code>chromosome_as_set</code>).
    </p>
  </div>
  <div class="card">
    <h3>Decoding</h3>
    <p>
      Turns the genes into the answer they stand for (<code>decode_func</code>).
      The genes are the genotype, the answer is the phenotype.
    </p>
  </div>
  <div class="card">
    <h3>Fitness and score</h3>
    <p>
      <code>fitness_func</code> gives each chromosome a <code>Score</code>.
      <code>minimize</code> says whether lower is better. A chromosome seen before is
      not scored again: its score is cached.
    </p>
  </div>
  <div class="card">
    <h3>Population and generation</h3>
    <p>
      The chromosomes alive at one time, always sorted best first. Each round of
      breeding makes a new generation.
    </p>
  </div>
</div>

{#if first && ran}
  <div class="card example">
    <h3>A real chromosome</h3>
    <p class="muted">The best of the random start, generation 0:</p>
    <div class="numbered">
      <div class="labelled">
        {#each first.genes as _, i (i)}<span>{i + 1}</span>{/each}
      </div>
      <GeneStrip genes={first.genes} off={off(first.genes, first.decoded)} size={30} />
    </div>
    <p>
      Genes <code>{first.genes.join('')}</code> ask for objects
      {first.genes.flatMap((g, i) => (g ? [i + 1] : [])).join(', ')}. Decoded, the bag
      holds objects {first.decoded.flatMap((g, i) => (g ? [i + 1] : [])).join(', ')}:
      the crossed-out genes asked for an object that no longer fit under the capacity
      of {ran.capacity}. Its score, the value of the bag, is <b>{fmt(first.score)}</b>.
    </p>
  </div>
{/if}

<h2>The loop</h2>
<svg class="loop" viewBox="0 0 960 250" role="img" aria-label="The steps of a run">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="var(--muted)" />
    </marker>
  </defs>
  {#each [
    { x: 20, y: 20, t: 'Random start', s: 'generation 0' },
    { x: 260, y: 20, t: 'Score and sort', s: 'best first' },
    { x: 500, y: 20, t: 'Stop?', s: 'checked each generation' },
    { x: 20, y: 160, t: 'Pick parents', s: 'best + random' },
    { x: 260, y: 160, t: 'Cross pairs', s: 'one cut each' },
    { x: 500, y: 160, t: 'Mutate children', s: 'redraw some genes' },
    { x: 740, y: 160, t: 'Keep the best', s: 'old + children, cut' },
  ] as box (box.t)}
    <rect x={box.x} y={box.y} width="200" height="64" rx="10" class="box" />
    <text x={box.x + 100} y={box.y + 28} text-anchor="middle" class="box-title">{box.t}</text>
    <text x={box.x + 100} y={box.y + 50} text-anchor="middle" class="box-sub">{box.s}</text>
  {/each}
  <path d="M220,52 L256,52" class="flow" />
  <path d="M460,52 L496,52" class="flow" />
  <path d="M700,52 L760,52" class="flow" />
  <text x="768" y="57" class="box-sub" text-anchor="start">yes: done</text>
  <path d="M560,84 L560,110 L120,110 L120,156" class="flow" />
  <text x="340" y="104" class="box-sub" text-anchor="middle">no: breed</text>
  <path d="M220,192 L256,192" class="flow" />
  <path d="M460,192 L496,192" class="flow" />
  <path d="M700,192 L736,192" class="flow" />
  <path d="M840,160 L840,132 L650,132 L650,88" class="flow back" />
  <text x="745" y="125" class="box-sub" text-anchor="middle">next generation</text>
</svg>

<h2>1. Pick the parents</h2>
<p>
  <code>crossovers_prop</code> sets how much of the population becomes parents,
  rounded down to an even number. <code>besties_prop</code> sets how many of those
  are the top of the population. The rest are drawn at random from everyone else,
  and one can be drawn twice. The parents are shuffled and paired in order.
</p>
{#if selection && fit}
  <p class="muted">
    In this run: {fit.population_size} × {fit.crossovers_prop} gives {selection.n}
    parents. {selection.n} × {fit.besties_prop} gives the {selection.best} best, plus
    {selection.random} at random.
  </p>
{/if}

<h2>2. Cross each pair</h2>
<p>
  Each pair is cut at one random point between the first and the last gene. One
  child takes the start of parent A and the end of parent B, the other child the
  opposite. Where both parents have the same gene, the child has it whatever the
  cut. Move the cut to see the children of a real pair of this run.
</p>
{#if parentA && parentB}
  <div class="card example">
    <div class="row"><span class="who">Parent A</span><GeneStrip genes={parentA.genes} size={26} /></div>
    <div class="row"><span class="who">Parent B</span><GeneStrip genes={parentB.genes} size={26} /></div>
    <label class="cut">
      <span>Cut after gene <b>{cut}</b></span>
      <input type="range" min="1" max={length - 1} bind:value={cut} />
    </label>
    {#each crossed as child, i (i)}
      <div class="row">
        <span class="who">Child {i + 1}</span>
        <GeneStrip genes={child.genes} origins={child.origins} size={26} />
      </div>
    {/each}
    <div class="key">
      <span><i class="bar a"></i>from parent A</span>
      <span><i class="bar b"></i>from parent B</span>
      <span><i class="bar both"></i>both parents have it</span>
    </div>
  </div>
{/if}

<h2>3. Mutate the children</h2>
<p>
  Each gene of each child is drawn again from the gene space with probability
  <code>mutate_prob</code>. A redrawn bit comes out the same half the time, so with
  the default 0.05 about 2.5% of the genes change. Mutation brings back genes the
  whole population had lost.
</p>
{#if mutated}
  <div class="card example">
    <div class="row"><span class="who">After crossing</span><GeneStrip genes={crossedGenes(mutated)} size={26} /></div>
    <div class="row">
      <span class="who">After mutation</span>
      <GeneStrip genes={mutated.genes} changed={mutated.changed} size={26} />
    </div>
    <p class="muted">
      A child of this run. The ringed genes changed: gene {mutated.changed
        .map((i) => i + 1)
        .join(' and gene ')}.
    </p>
  </div>
{/if}

<h2>4. Keep the best</h2>
<p>
  The children join the old population. All of them are scored, sorted, and only
  the best <code>population_size</code> stay. A child stays only if it beats an old
  chromosome. So the best score never goes down from one generation to the next.
</p>

<h2>When it stops</h2>
<ul>
  <li>After <code>n_generations</code> generations.</li>
  <li>
    When fewer than <code>min_population_size</code> different chromosomes are left.
    The population has become copies of a few.
  </li>
  <li>
    When the mean score equals the one of the generation before, if
    <code>stop_without_improvement</code> is on. It is on by default, and often ends
    a run early.
  </li>
  <li>When an <code>exit_condition</code> given to <code>fit</code> says so.</li>
</ul>

<h2>The parameters</h2>
<div class="card scroll">
  <table>
    <thead>
      <tr><th>FitConfig field</th><th>Default</th><th>What it does</th></tr>
    </thead>
    <tbody>
      <tr><td><code>population_size</code></td><td>none</td><td>Chromosomes in each generation.</td></tr>
      <tr><td><code>n_generations</code></td><td>none</td><td>Generations bred after the first, at most.</td></tr>
      <tr><td><code>crossovers_prop</code></td><td>0.7</td><td>Share of the population picked as parents.</td></tr>
      <tr><td><code>besties_prop</code></td><td>0.6</td><td>Share of the parents taken from the top.</td></tr>
      <tr><td><code>mutate_prob</code></td><td>0.05</td><td>Chance that a gene of a child is redrawn.</td></tr>
      <tr><td><code>min_population_size</code></td><td>10</td><td>Stop below this many different chromosomes.</td></tr>
      <tr><td><code>stop_without_improvement</code></td><td>on</td><td>Stop when the mean score stalls.</td></tr>
      <tr><td><code>n_jobs</code></td><td>-2</td><td>Processes that score chromosomes. This site uses 1.</td></tr>
    </tbody>
  </table>
</div>

<h2>Try it</h2>
<p>
  <a href="#/knapsack">Knapsack</a> runs the example with your own objects and
  parameters. <a href="#/function">Find a maximum</a> runs a problem where each
  chromosome stands for a number. Both let you step through every generation.
</p>

<style>
  .scroll {
    overflow-x: auto;
  }
  .terms {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 0.8rem;
  }
  .terms h3 {
    margin-top: 0;
  }
  .terms p {
    margin: 0;
  }
  .example {
    margin-top: 0.8rem;
  }
  .example h3 {
    margin-top: 0;
  }
  .numbered {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    margin-bottom: 0.4rem;
  }
  .labelled {
    display: flex;
    gap: 2px;
    color: var(--muted);
  }
  .labelled span {
    width: 30px;
    text-align: center;
    font-size: 0.85rem;
  }
  .loop {
    width: 100%;
    height: auto;
    max-height: 280px;
  }
  .box {
    fill: var(--bg-surface);
    stroke: var(--axis);
    stroke-width: 1.5;
  }
  .box-title {
    fill: var(--text);
    font-weight: 600;
    font-size: 18px;
  }
  .box-sub {
    fill: var(--text-2);
    font-size: 15px;
  }
  .flow {
    fill: none;
    stroke: var(--muted);
    stroke-width: 2;
    marker-end: url(#arrow);
  }
  .flow.back {
    stroke-dasharray: 5 4;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin: 0.3rem 0;
  }
  .who {
    width: 9rem;
    color: var(--text-2);
  }
  .cut {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 0.6rem 0;
  }
  .cut input {
    flex: 1;
  }
  .key {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1.2rem;
    color: var(--text-2);
    margin-top: 0.4rem;
  }
  .bar {
    display: inline-block;
    width: 18px;
    height: 4px;
    border-radius: 2px;
    vertical-align: middle;
    margin-right: 0.4rem;
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
</style>
